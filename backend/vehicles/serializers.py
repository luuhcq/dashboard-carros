"""Serializers de vehicles.

Nenhuma métrica financeira é recalculada aqui — tudo vem de
VehicleMetricsService.calculate() (Prompt 12). Este módulo só formata pra
exibição (arredondamento + string) o que o service já calculou.
"""

from decimal import ROUND_HALF_UP, Decimal

from rest_framework import serializers

from .models import Vehicle, VehicleExpense, VehiclePhoto, VehicleStatus, VehicleValueChangeLog
from .services import VehicleMetrics, VehicleMetricsService

# Arredondamento de exibição das métricas derivadas — decisão tomada aqui,
# não estava especificada antes (VehicleMetricsService devolve Decimal com
# precisão total, 20+ casas, de propósito, pra não perder precisão no
# cálculo — ver Prompt 12).
#
# - Frações (percentuais/razões: margem, ROI, % FIPE pago, desconto FIPE):
#   4 casas decimais. O frontend multiplica por 100 e formata como
#   percentual (0.1471 -> "14.71%").
# - Valores monetários (totais, lucro, lucro/dia): 2 casas decimais, como
#   qualquer outro campo monetário do sistema (mesmo padrão dos DecimalField
#   do model: max_digits=14, decimal_places=2).
# - days_in_stock (int) e aging_bucket (str) passam direto, sem arredondar.
#
# Tudo sai como string (nunca Decimal cru, nunca float) — mesma garantia que
# um DecimalField do DRF já dá pros campos do model.

FRACTION_METRIC_FIELDS = {
    'fipe_percentage_paid',
    'fipe_discount',
    'projected_margin',
    'projected_roi',
    'margin',
    'roi',
}
MONEY_METRIC_FIELDS = {
    'total_expenses',
    'total_cost',
    'projected_profit',
    'profit',
    'profit_per_day',
}
FRACTION_QUANTIZE = Decimal('0.0001')
MONEY_QUANTIZE = Decimal('0.01')


def _round_metric_for_display(field_name, value):
    """Arredonda (se for Decimal) e converte pra string. None permanece None
    (vira `null` explícito no JSON, nunca chave ausente)."""
    if value is None:
        return None
    if field_name in FRACTION_METRIC_FIELDS:
        return str(value.quantize(FRACTION_QUANTIZE, rounding=ROUND_HALF_UP))
    if field_name in MONEY_METRIC_FIELDS:
        return str(value.quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP))
    return value  # days_in_stock (int) / aging_bucket (str)


def _serialize_metrics(metrics: VehicleMetrics) -> dict:
    return {
        field_name: _round_metric_for_display(field_name, getattr(metrics, field_name))
        for field_name in metrics.__dataclass_fields__
    }


class VehicleListSerializer(serializers.ModelSerializer):
    """Campos resumidos pra tabela de estoque, + os calculados que aparecem
    nela: total_cost, margin (projected_margin ou margin, dependendo se já
    foi vendido), aging_bucket, days_in_stock.

    N+1 conhecido: cada linha desta listagem chama
    VehicleMetricsService.calculate() sem total_expenses pré-calculado, o
    que dispara uma query de soma por veículo. Resolver isso é
    responsabilidade do ViewSet (annotate + Sum no queryset, passado via
    contexto), que ainda não existe — fora do escopo deste prompt (só
    serializers). O service já foi desenhado em Prompt 12 justamente para
    aceitar esse valor pré-calculado quando essa camada existir.
    """

    total_cost = serializers.SerializerMethodField()
    margin = serializers.SerializerMethodField()
    aging_bucket = serializers.SerializerMethodField()
    days_in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id',
            'internal_code',
            'brand',
            'model',
            'model_year',
            'mileage',
            'status',
            'purchase_date',
            'fipe_reference_value',
            'asking_price',
            'total_cost',
            'margin',
            'aging_bucket',
            'days_in_stock',
        ]
        read_only_fields = fields

    def _metrics(self, vehicle: Vehicle) -> VehicleMetrics:
        cache = getattr(self, '_metrics_cache', None)
        if cache is None:
            cache = {}
            self._metrics_cache = cache
        if vehicle.pk not in cache:
            cache[vehicle.pk] = VehicleMetricsService.calculate(vehicle)
        return cache[vehicle.pk]

    def get_total_cost(self, vehicle):
        return _round_metric_for_display('total_cost', self._metrics(vehicle).total_cost)

    def get_margin(self, vehicle):
        metrics = self._metrics(vehicle)
        value = metrics.margin if vehicle.status == VehicleStatus.SOLD else metrics.projected_margin
        return _round_metric_for_display('margin', value)

    def get_aging_bucket(self, vehicle):
        return self._metrics(vehicle).aging_bucket

    def get_days_in_stock(self, vehicle):
        return self._metrics(vehicle).days_in_stock


class VehicleDetailSerializer(serializers.ModelSerializer):
    """Todos os campos do model + todas as 13 métricas do
    VehicleMetricsService embutidas em `metrics` (objeto aninhado, não
    campos soltos — decisão tomada aqui: um único SerializerMethodField que
    calcula tudo de uma vez, em vez de 13 métodos separados que arriscariam
    recalcular o service 13x pro mesmo veículo).

    Somente leitura por enquanto: não existe endpoint de escrita de Vehicle
    definido em nenhum prompt até aqui (regras de transição de status,
    imutabilidade de internal_code em runtime de API etc. ainda não foram
    especificadas) — esse serializer cobre só o que foi pedido: detalhe +
    métricas.
    """

    metrics = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id',
            'internal_code',
            'company',
            'brand',
            'model',
            'version',
            'manufacture_year',
            'model_year',
            'mileage',
            'plate',
            'chassis',
            'color',
            'status',
            'source',
            'supplier_name',
            'purchase_date',
            'purchase_price',
            'fipe_reference_value',
            'fipe_code',
            'asking_price',
            'sale_date',
            'sale_price',
            'notes',
            'deleted_at',
            'deletion_reason',
            'created_at',
            'updated_at',
            'metrics',
        ]
        read_only_fields = fields

    def get_metrics(self, vehicle):
        return _serialize_metrics(VehicleMetricsService.calculate(vehicle))


class VehicleExpenseSerializer(serializers.ModelSerializer):
    """Leitura e escrita. deleted_at/deletion_reason ficam visíveis na
    saída (útil pra investigação — mesmo raciocínio do Admin no Prompt 11),
    mas nunca graváveis por aqui: soft delete tem seu próprio fluxo (fora do
    escopo deste prompt), nunca um PATCH direto nesses campos."""

    class Meta:
        model = VehicleExpense
        fields = [
            'id',
            'vehicle',
            'date',
            'category',
            'description',
            'supplier',
            'amount',
            'paid',
            'notes',
            'deleted_at',
            'deletion_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'deleted_at', 'deletion_reason', 'created_at', 'updated_at']


class VehicleValueChangeLogSerializer(serializers.ModelSerializer):
    """Somente leitura — reflete que VehicleValueChangeLog é um log
    append-only (save()/delete() já bloqueados no model, ver Prompt 09).

    read_only_fields sozinho não é suficiente pra deixar isso
    "estruturalmente impossível" (um serializer com todos os campos
    read-only ainda aceita .save(), só que chamando create()/update() do
    model com validated_data vazio — o que estouraria como erro de banco,
    não como recusa limpa). Por isso create()/update() são sobrescritos pra
    recusar explicitamente, então mesmo que um ViewSet futuro esqueça de
    restringir os métodos HTTP, o serializer barra sozinho.
    """

    class Meta:
        model = VehicleValueChangeLog
        fields = [
            'id',
            'vehicle',
            'field_name',
            'old_value',
            'new_value',
            'reason',
            'changed_at',
            'created_at',
        ]
        read_only_fields = fields

    def create(self, validated_data):
        raise NotImplementedError(
            'VehicleValueChangeLogSerializer é somente leitura; '
            'VehicleValueChangeLog é append-only e não tem endpoint de escrita.'
        )

    def update(self, instance, validated_data):
        raise NotImplementedError(
            'VehicleValueChangeLogSerializer é somente leitura; '
            'VehicleValueChangeLog nunca é editável após criado.'
        )


class VehiclePhotoSerializer(serializers.ModelSerializer):
    """Leitura e escrita. thumbnail é gerado automaticamente no save() do
    model (Prompt 10) — nunca aceito como entrada."""

    class Meta:
        model = VehiclePhoto
        fields = ['id', 'vehicle', 'image', 'thumbnail', 'position', 'is_cover', 'created_at']
        read_only_fields = ['id', 'thumbnail', 'created_at']
