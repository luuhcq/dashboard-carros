"""Endpoints agregados de dashboard (Prompt 20).

Reaproveita vehicles.querysets.annotate_vehicle_metrics() (Prompt 19) —
nenhuma métrica é recalculada em Python por veículo aqui, tudo é Sum/Avg/
Count resolvido no banco sobre o queryset já anotado. "Em estoque" =
status != SOLD, usado em summary/ e aging/; status/ é o único que conta
TODOS os veículos, inclusive vendidos.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import AGING_BUCKET_RANGES
from .models import Vehicle, VehicleStatus
from .querysets import annotate_vehicle_metrics

DashboardSummarySerializer = inline_serializer(
    'DashboardSummarySerializer',
    fields={
        'vehicles_in_stock': serializers.IntegerField(),
        'capital_employed': serializers.CharField(),
        'total_asking_price': serializers.CharField(),
        'potential_profit': serializers.CharField(),
        'average_aging_days': serializers.FloatField(allow_null=True),
    },
)

# Chaves dos buckets ('0-15', '90+' etc.) não são identificadores Python
# válidos, então não dá pra declarar como campos de uma classe Serializer
# normal — inline_serializer aceita o dict de fields diretamente.
DashboardAgingSerializer = inline_serializer(
    'DashboardAgingSerializer',
    fields={
        **{bucket: serializers.IntegerField() for bucket in AGING_BUCKET_RANGES},
        '90+': serializers.IntegerField(),
    },
)

DashboardStatusSerializer = inline_serializer(
    'DashboardStatusSerializer',
    fields={choice: serializers.IntegerField() for choice, _ in VehicleStatus.choices},
)

MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)
ZERO_MONEY = Value(Decimal('0'), output_field=MONEY_FIELD)


def _money(value: Decimal) -> str:
    return str(Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


class DashboardSummaryView(APIView):
    """GET /api/dashboard/summary/ — agregado sobre veículos em estoque
    (status != SOLD).

    Decisão sobre estoque vazio (documentada aqui, não deixada implícita):
    vehicles_in_stock/capital_employed/total_asking_price/potential_profit
    voltam 0 — são somas/contagens, e a soma de um conjunto vazio é 0 por
    definição matemática, sem ambiguidade. average_aging_days volta null —
    a MÉDIA de um conjunto vazio é indefinida, não zero; forçar 0 aqui
    sugeriria falsamente "os veículos em estoque têm 0 dias de idade em
    média", quando na verdade não há veículos pra calcular média nenhuma.
    """

    @extend_schema(
        responses={200: DashboardSummarySerializer},
        description=(
            'Agregado financeiro sobre veículos em estoque (status != SOLD): capital '
            'empregado, preço de venda pedido total, lucro potencial e aging médio. '
            'Estoque vazio: somas/contagem voltam 0, average_aging_days volta null '
            '(média de conjunto vazio é indefinida, não zero).'
        ),
    )
    def get(self, request):
        queryset = annotate_vehicle_metrics(Vehicle.objects.exclude(status=VehicleStatus.SOLD))

        aggregates = queryset.aggregate(
            vehicles_in_stock=Count('id'),
            capital_employed=Coalesce(Sum('total_cost'), ZERO_MONEY),
            total_asking_price=Coalesce(
                Sum('asking_price', filter=Q(asking_price__isnull=False)), ZERO_MONEY
            ),
            potential_profit=Coalesce(
                Sum(F('asking_price') - F('total_cost'), filter=Q(asking_price__isnull=False)),
                ZERO_MONEY,
            ),
            average_aging_days=Avg('days_in_stock'),
        )

        average_aging = aggregates['average_aging_days']
        if average_aging is not None:
            average_aging = float(
                Decimal(str(average_aging)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            )

        return Response({
            'vehicles_in_stock': aggregates['vehicles_in_stock'],
            'capital_employed': _money(aggregates['capital_employed']),
            'total_asking_price': _money(aggregates['total_asking_price']),
            'potential_profit': _money(aggregates['potential_profit']),
            'average_aging_days': average_aging,
        })


class DashboardAgingView(APIView):
    """GET /api/dashboard/aging/ — contagem por faixa de aging, só veículos
    em estoque (status != SOLD). Reaproveita AGING_BUCKET_RANGES de
    vehicles.filters — os mesmos buckets do filtro de listagem (Prompt 19),
    não redefinidos aqui. Estoque vazio: cada bucket volta 0 (Count nunca
    retorna None, mesmo sobre conjunto vazio — sem ambiguidade a tratar)."""

    @extend_schema(
        responses={200: DashboardAgingSerializer},
        description=(
            'Contagem de veículos em estoque (status != SOLD) por faixa de aging '
            '(dias desde purchase_date), nos mesmos buckets do filtro aging_bucket '
            'de GET /api/vehicles/. Todo bucket aparece mesmo com 0 veículos.'
        ),
    )
    def get(self, request):
        queryset = annotate_vehicle_metrics(Vehicle.objects.exclude(status=VehicleStatus.SOLD))

        bucket_filters = {
            bucket: Count('id', filter=Q(days_in_stock__gte=low, days_in_stock__lte=high))
            for bucket, (low, high) in AGING_BUCKET_RANGES.items()
        }
        bucket_filters['90+'] = Count('id', filter=Q(days_in_stock__gt=90))

        return Response(queryset.aggregate(**bucket_filters))


class DashboardStatusView(APIView):
    """GET /api/dashboard/status/ — contagem por status, TODOS os veículos
    (inclusive SOLD — diferente de summary/ e aging/ acima). Todo status do
    enum aparece no payload, mesmo com 0 veículos, pra o frontend não
    precisar tratar chave ausente como caso especial."""

    @extend_schema(
        responses={200: DashboardStatusSerializer},
        description=(
            'Contagem de TODOS os veículos por status, inclusive SOLD (diferente de '
            'summary/ e aging/, que só olham estoque). Todo status do enum aparece '
            'no payload mesmo com 0 veículos.'
        ),
    )
    def get(self, request):
        counts = {choice: 0 for choice, _ in VehicleStatus.choices}
        for row in Vehicle.objects.values('status').annotate(count=Count('id')):
            counts[row['status']] = row['count']
        return Response(counts)
