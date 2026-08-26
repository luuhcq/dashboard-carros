"""Cálculo financeiro derivado de Vehicle — nunca duplicar essa lógica no
frontend nem em serializers/views. Nenhuma métrica aqui é persistida como
coluna; tudo é calculado sob demanda a partir de Vehicle/VehicleExpense.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db.models import Sum
from django.utils import timezone

from vehicles.models import Vehicle, VehicleExpense, VehicleStatus

ZERO = Decimal('0')
ONE = Decimal('1')


@dataclass(frozen=True)
class VehicleMetrics:
    total_expenses: Decimal
    total_cost: Decimal
    fipe_percentage_paid: Optional[Decimal]
    fipe_discount: Optional[Decimal]
    projected_profit: Optional[Decimal]
    projected_margin: Optional[Decimal]
    projected_roi: Optional[Decimal]
    profit: Optional[Decimal]
    margin: Optional[Decimal]
    roi: Optional[Decimal]
    days_in_stock: int
    aging_bucket: str
    profit_per_day: Optional[Decimal]


def _safe_divide(numerator: Optional[Decimal], denominator: Optional[Decimal]) -> Optional[Decimal]:
    """numerator/denominator, mas None se qualquer um dos dois for None ou se
    o denominador for zero — nunca lança ZeroDivisionError. numerator e
    denominator, quando não-None, já precisam ser Decimal (nunca float)."""
    if numerator is None or denominator is None or denominator == ZERO:
        return None
    return numerator / denominator


def _get_total_expenses(vehicle: Vehicle) -> Decimal:
    # Filtra explicitamente por VehicleExpense.objects (manager com soft
    # delete) em vez de usar vehicle.expenses — não depende de qual manager
    # o Django escolhe por padrão pro related manager reverso, então o
    # comportamento é o mesmo independentemente disso.
    aggregate = VehicleExpense.objects.filter(vehicle_id=vehicle.id).aggregate(total=Sum('amount'))
    return aggregate['total'] or ZERO


def _aging_bucket(days_in_stock: int) -> str:
    """Faixas fixadas pelo briefing (0-15/16-30/31-45/46-60/61-90/90+).

    Duplicado de propósito, não composição: vehicles.filters.
    AGING_BUCKET_RANGES tem os mesmos limites pra uso em SQL (filtro
    aging_bucket= e dashboard-aging), porque aqui é comparação em Python
    (int) e lá é usado dentro de Q()/Count() do ORM — não dá pra
    compartilhar a mesma estrutura sem acoplar os dois módulos por pouco
    ganho. Se as faixas mudarem, mudam nos dois lugares — não há teste
    automático hoje que pegue divergência entre eles."""
    if days_in_stock <= 15:
        return '0-15'
    if days_in_stock <= 30:
        return '16-30'
    if days_in_stock <= 45:
        return '31-45'
    if days_in_stock <= 60:
        return '46-60'
    if days_in_stock <= 90:
        return '61-90'
    return '90+'


class VehicleMetricsService:
    @staticmethod
    def calculate(vehicle: Vehicle, total_expenses: Optional[Decimal] = None, today=None) -> VehicleMetrics:
        """Calcula todas as métricas financeiras derivadas de um Vehicle.

        total_expenses: passe já calculado (ex.: via annotate() com Sum
        filtrado por deleted_at__isnull=True numa listagem de Vehicles) pra
        pular a query de agregação e evitar N+1. Se omitido, é calculado
        aqui com uma query própria.

        today: injetável só pra permitir teste determinístico de
        days_in_stock; em produção, omitir usa a data atual.
        """
        if total_expenses is None:
            total_expenses = _get_total_expenses(vehicle)

        total_cost = vehicle.purchase_price + total_expenses

        fipe_percentage_paid = _safe_divide(vehicle.purchase_price, vehicle.fipe_reference_value)
        fipe_discount = None if fipe_percentage_paid is None else ONE - fipe_percentage_paid

        if vehicle.asking_price is None:
            projected_profit = None
            projected_margin = None
            projected_roi = None
        else:
            projected_profit = vehicle.asking_price - total_cost
            projected_margin = _safe_divide(projected_profit, vehicle.asking_price)
            projected_roi = _safe_divide(projected_profit, total_cost)

        if vehicle.status == VehicleStatus.SOLD and vehicle.sale_price is not None:
            profit = vehicle.sale_price - total_cost
            margin = _safe_divide(profit, vehicle.sale_price)
            roi = _safe_divide(profit, total_cost)
        else:
            profit = None
            margin = None
            roi = None

        if vehicle.status == VehicleStatus.SOLD and vehicle.sale_date is not None:
            days_in_stock = (vehicle.sale_date - vehicle.purchase_date).days
        else:
            reference_date = today if today is not None else timezone.localdate()
            days_in_stock = (reference_date - vehicle.purchase_date).days

        aging_bucket = _aging_bucket(days_in_stock)

        # Deliberado: profit_per_day usa "profit" (realizado, só existe se
        # vendido), não "projected_profit" — não faz sentido "lucro por dia"
        # de um veículo que ainda nem foi vendido.
        if profit is None or days_in_stock == 0:
            profit_per_day = None
        else:
            profit_per_day = profit / days_in_stock

        return VehicleMetrics(
            total_expenses=total_expenses,
            total_cost=total_cost,
            fipe_percentage_paid=fipe_percentage_paid,
            fipe_discount=fipe_discount,
            projected_profit=projected_profit,
            projected_margin=projected_margin,
            projected_roi=projected_roi,
            profit=profit,
            margin=margin,
            roi=roi,
            days_in_stock=days_in_stock,
            aging_bucket=aging_bucket,
            profit_per_day=profit_per_day,
        )
