"""Annotations de queryset para Vehicle (Prompt 19).

Resolve em SQL o que VehicleMetricsService (Prompt 12) calcula em Python
linha a linha — especificamente os campos usados em ordenação/filtro da
listagem: total_cost, days_in_stock, margin, roi. É isso que fecha
o N+1 documentado como limitação conhecida no Prompt 14 (decisão 4):
antes, VehicleListSerializer chamava VehicleMetricsService.calculate() por
veículo (uma query de soma de despesas por linha); agora esse cálculo sai
inteiro em uma única query, com annotate()/Case()/Sum().

A lógica condicional (SOLD vs não, denominador zero/nulo -> None) replica
exatamente a do service — testada explicitamente contra
VehicleMetricsService em vehicles/test_querysets.py para os dois
concordarem sempre, não só "parecerem certos".
"""

from decimal import Decimal

from django.db.models import Case, DateField, DecimalField, F, Q, QuerySet, Sum, Value, When
from django.db.models.functions import Coalesce, Extract, NullIf
from django.utils import timezone

from .models import VehicleStatus

MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)
RATIO_FIELD = DecimalField(max_digits=20, decimal_places=10)

ZERO_MONEY = Value(Decimal('0'), output_field=MONEY_FIELD)
ZERO_RATIO = Value(Decimal('0'), output_field=RATIO_FIELD)
NULL_RATIO = Value(None, output_field=RATIO_FIELD)


def annotate_vehicle_metrics(queryset: QuerySet, today=None) -> QuerySet:
    """Annotates no queryset de Vehicle: total_expenses, total_cost,
    days_in_stock (int, dias em estoque), margin, roi.

    days_in_stock (Prompt 23): nome unificado com o campo homônimo exposto
    pelos serializers e VehicleMetricsService — antes a annotation se
    chamava `aging`, nome diferente do que a API expunha (`days_in_stock`),
    então `?ordering=` usava um nome e a resposta JSON usava outro pro
    mesmo valor. aging_bucket e /api/dashboard/aging/ não mudaram — esses
    são sobre o conceito de faixa/distribuição, não o número cru.

    today: injetável só pra teste determinístico (mesmo propósito do
    parâmetro equivalente em VehicleMetricsService.calculate).
    """
    today = today or timezone.localdate()

    total_expenses_expr = Coalesce(
        Sum('expenses__amount', filter=Q(expenses__deleted_at__isnull=True)),
        Value(0),
        output_field=MONEY_FIELD,
    )

    # sale_date__isnull=False é necessário: se status==SOLD mas sale_date
    # for None (caso de borda só alcançável via ORM direto), o service cai
    # pra today - purchase_date — sem essa condição, a subtração com NULL
    # daria NULL aqui, divergindo do Python.
    aging_diff = Case(
        When(
            status=VehicleStatus.SOLD,
            sale_date__isnull=False,
            then=F('sale_date') - F('purchase_date'),
        ),
        default=Value(today, output_field=DateField()) - F('purchase_date'),
    )

    # Duas annotate() separados: total_cost depende de total_expenses já
    # resolvido, então precisa vir depois (o ORM não deixa referenciar uma
    # annotation dentro da mesma chamada que a declara).
    queryset = queryset.annotate(
        total_expenses=total_expenses_expr,
        days_in_stock=Extract(aging_diff, 'day'),
    ).annotate(
        total_cost=F('purchase_price') + F('total_expenses'),
    )

    projected_profit_expr = F('asking_price') - F('total_cost')
    profit_expr = F('sale_price') - F('total_cost')

    # margin/roi replicam a árvore de decisão do service:
    # - status == SOLD: usa sale_price (se presente; senão None — NÃO cai
    #   pra projected, mesmo comportamento de VehicleMetricsService).
    # - caso contrário: usa asking_price (se presente; senão None).
    # NullIf(denominador, 0) evita erro de divisão por zero no Postgres —
    # sem isso, um asking_price/sale_price/total_cost = 0 quebraria a
    # query inteira, não só a linha (diferente do Python, que já trata
    # isso por linha em _safe_divide).
    margin_sold = Case(
        When(sale_price__isnull=False, then=profit_expr / NullIf(F('sale_price'), ZERO_RATIO)),
        default=NULL_RATIO,
        output_field=RATIO_FIELD,
    )
    margin_not_sold = Case(
        When(
            asking_price__isnull=False,
            then=projected_profit_expr / NullIf(F('asking_price'), ZERO_RATIO),
        ),
        default=NULL_RATIO,
        output_field=RATIO_FIELD,
    )
    margin_expr = Case(
        When(status=VehicleStatus.SOLD, then=margin_sold),
        default=margin_not_sold,
        output_field=RATIO_FIELD,
    )

    roi_sold = Case(
        When(sale_price__isnull=False, then=profit_expr / NullIf(F('total_cost'), ZERO_RATIO)),
        default=NULL_RATIO,
        output_field=RATIO_FIELD,
    )
    roi_not_sold = Case(
        When(
            asking_price__isnull=False,
            then=projected_profit_expr / NullIf(F('total_cost'), ZERO_RATIO),
        ),
        default=NULL_RATIO,
        output_field=RATIO_FIELD,
    )
    roi_expr = Case(
        When(status=VehicleStatus.SOLD, then=roi_sold),
        default=roi_not_sold,
        output_field=RATIO_FIELD,
    )

    return queryset.annotate(margin=margin_expr, roi=roi_expr)
