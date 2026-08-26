"""Serializers de vehicles.

Nenhuma métrica financeira é recalculada aqui — tudo vem de
VehicleMetricsService.calculate() (Prompt 12). Este módulo só formata pra
exibição (arredondamento + string) o que o service já calculou.
"""

from decimal import ROUND_HALF_UP, Decimal

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Vehicle, VehicleExpense, VehiclePhoto, VehicleStatus, VehicleValueChangeLog
from .services import VehicleMetrics, VehicleMetricsService
from .services import _aging_bucket as _compute_aging_bucket

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
#
# Modo de arredondamento: ROUND_HALF_UP explícito em toda parte, nunca o
# default do Python (ROUND_HALF_EVEN / "banker's rounding"). Decisão
# deliberada, não a que teria saído se eu só chamasse quantize() sem
# especificar rounding=: é o comportamento que qualquer usuário não-técnico
# espera de um sistema financeiro (0,125 -> 0,13, não 0,12) — confirmado com
# testes de borda específicos em test_serializers.py::RoundingModeTests que
# provam a divergência real entre os dois modos, não só que um valor
# genérico "deu certo".

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

    N+1 resolvido (Prompt 19): quando o queryset já vem anotado por
    vehicles.querysets.annotate_vehicle_metrics() — é isso que
    VehicleViewSet.get_queryset() faz pra list() —, os campos calculados
    são lidos direto dos atributos anotados na instância (populados em SQL,
    zero query extra por linha). A checagem usa hasattr(), não
    "valor is not None": margin/roi podem ser legitimamente None mesmo
    anotados (ex. sem asking_price), então checar por None erradamente
    dispararia o fallback abaixo e reintroduziria o N+1 pra esses casos.

    Se o serializer for usado sobre um queryset SEM essa annotation (ex.
    instanciado direto sobre um objeto solto), cai pra chamar
    VehicleMetricsService por linha — mantém compatibilidade, mas isso
    reintroduziria o N+1 se usado assim numa listagem de verdade.
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
        """Fallback só usado quando o queryset não veio anotado."""
        cache = getattr(self, '_metrics_cache', None)
        if cache is None:
            cache = {}
            self._metrics_cache = cache
        if vehicle.pk not in cache:
            cache[vehicle.pk] = VehicleMetricsService.calculate(vehicle)
        return cache[vehicle.pk]

    @extend_schema_field(OpenApiTypes.STR)
    def get_total_cost(self, vehicle):
        if hasattr(vehicle, 'total_cost'):
            return _round_metric_for_display('total_cost', vehicle.total_cost)
        return _round_metric_for_display('total_cost', self._metrics(vehicle).total_cost)

    @extend_schema_field(OpenApiTypes.STR)
    def get_margin(self, vehicle):
        if hasattr(vehicle, 'margin'):
            return _round_metric_for_display('margin', vehicle.margin)
        metrics = self._metrics(vehicle)
        value = metrics.margin if vehicle.status == VehicleStatus.SOLD else metrics.projected_margin
        return _round_metric_for_display('margin', value)

    @extend_schema_field(OpenApiTypes.STR)
    def get_aging_bucket(self, vehicle):
        if hasattr(vehicle, 'days_in_stock'):
            return _compute_aging_bucket(vehicle.days_in_stock)
        return self._metrics(vehicle).aging_bucket

    @extend_schema_field(OpenApiTypes.INT)
    def get_days_in_stock(self, vehicle):
        if hasattr(vehicle, 'days_in_stock'):
            return vehicle.days_in_stock
        return self._metrics(vehicle).days_in_stock


class VehicleMetricsSerializer(serializers.Serializer):
    """Formato do objeto `metrics` embutido em VehicleDetailSerializer — só
    pra descrição de schema (get_metrics devolve um dict simples, não uma
    instância deste serializer). Campos espelham VehicleMetrics
    (services.py); todos vêm formatados como string (ver
    _round_metric_for_display), exceto days_in_stock (int) e aging_bucket
    (str). Campos calculados a partir de sale_price (profit/margin/roi/
    profit_per_day) são null enquanto o veículo não foi vendido."""

    total_expenses = serializers.CharField()
    total_cost = serializers.CharField()
    fipe_percentage_paid = serializers.CharField(allow_null=True)
    fipe_discount = serializers.CharField(allow_null=True)
    projected_profit = serializers.CharField(allow_null=True)
    projected_margin = serializers.CharField(allow_null=True)
    projected_roi = serializers.CharField(allow_null=True)
    profit = serializers.CharField(allow_null=True)
    margin = serializers.CharField(allow_null=True)
    roi = serializers.CharField(allow_null=True)
    days_in_stock = serializers.IntegerField()
    aging_bucket = serializers.CharField()
    profit_per_day = serializers.CharField(allow_null=True)


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

    @extend_schema_field(VehicleMetricsSerializer)
    def get_metrics(self, vehicle):
        return _serialize_metrics(VehicleMetricsService.calculate(vehicle))


class VehicleWriteSerializer(serializers.ModelSerializer):
    """Serializer de escrita (create + PATCH parcial) — separado dos de
    leitura (Prompt 14), que continuam somente-leitura de propósito.

    asking_price/sale_price são bloqueados em TODA escrita por aqui — create
    e PATCH, sem exceção. Não existe caminho de criação ou edição de Vehicle
    que grave esses dois campos diretamente; a única forma de defini-los ou
    alterá-los é pelos endpoints dedicados POST /api/vehicles/{id}/price/ e
    /sale/ (Prompt 17, em vehicles/views.py), que geram o
    VehicleValueChangeLog com justificativa obrigatória — inclusive a
    primeira definição do valor precisa desse registro de auditoria (com
    old_value=None), não só mudanças posteriores.

    Decisão sobre requisição com campo proibido junto de campos válidos
    (confirmada com o usuário): rejeita a REQUISIÇÃO INTEIRA — 400, nada é
    persistido, nem os outros campos do mesmo payload. Um 400 que ainda
    assim aplica parte do pedido seria uma combinação confusa pra quem
    consome a API: a resposta diz que falhou, mas o servidor mudou estado
    mesmo assim. Rejeição total mantém o significado usual de um 400 (nada
    mudou) e é mais simples de testar.
    """

    NEVER_WRITABLE_FIELDS = {'asking_price', 'sale_price'}

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
        ]
        read_only_fields = [
            'id',
            'internal_code',
            'deleted_at',
            'deletion_reason',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs):
        blocked_present = self.NEVER_WRITABLE_FIELDS & set(attrs.keys())
        if blocked_present:
            raise serializers.ValidationError({
                field_name: (
                    'Não é possível gravar este campo por aqui, nem na criação nem '
                    'na edição. A definição/alteração de asking_price/sale_price '
                    'precisa passar pelos endpoints dedicados (Prompt 17), que '
                    'registram o motivo da mudança.'
                )
                for field_name in sorted(blocked_present)
            })

        # status=SOLD só pode acontecer via POST /api/vehicles/{id}/sale/
        # (Prompt 17) — esse é o único caminho que cria o
        # VehicleValueChangeLog e garante sale_price/sale_date consistentes.
        # Sem essa checagem, um PATCH {"status": "SOLD"} produziria um
        # veículo "vendido" sem preço de venda e sem log nenhum.
        if attrs.get('status') == VehicleStatus.SOLD:
            raise serializers.ValidationError({
                'status': (
                    'Não é possível definir status=SOLD por aqui. Use '
                    'POST /api/vehicles/{id}/sale/, que também registra o '
                    'preço de venda e o motivo.'
                )
            })

        instance = self.instance

        # Simetria da regra acima: uma vez SOLD, sair desse status por aqui
        # também é bloqueado. Sem isso, PATCH {"status": "LISTED"} num
        # veículo já vendido passava despercebido — sale_price/sale_date
        # ficavam presos no banco sem log nenhum sobre a reversão, e o
        # veículo parecia "não vendido" pro status mas continuava com dados
        # de venda íntegros. Reverter um SOLD é uma decisão de negócio que
        # precisa dizer o que fazer com esses dados — não está implementada
        # ainda, então o caminho fica fechado por enquanto.
        if (
            instance is not None
            and instance.status == VehicleStatus.SOLD
            and 'status' in attrs
            and attrs['status'] != VehicleStatus.SOLD
        ):
            raise serializers.ValidationError({
                'status': (
                    'Não é possível sair de status=SOLD por aqui. Reverter uma '
                    'venda exige decidir o que fazer com sale_price/sale_date/'
                    'histórico — esse fluxo ainda não existe.'
                )
            })

        def resolve(field_name):
            if field_name in attrs:
                return attrs[field_name]
            return getattr(instance, field_name) if instance is not None else None

        # sale_date continua gravável por aqui (só asking_price/sale_price são
        # bloqueados), então a validação cruzada com purchase_date permanece.
        purchase_date = resolve('purchase_date')
        sale_date = resolve('sale_date')
        if sale_date is not None and purchase_date is not None and sale_date < purchase_date:
            raise serializers.ValidationError(
                {'sale_date': 'sale_date não pode ser anterior a purchase_date.'}
            )

        # sale_price > 0 e asking_price >= 0 não têm mais checagem aqui: como
        # os dois são sempre bloqueados acima antes de chegar neste ponto,
        # qualquer verificação de valor para eles seria código morto,
        # inalcançável. purchase_price/fipe_reference_value continuam
        # graváveis normalmente, então mantêm a checagem de não-negativo.
        for field_name in ('purchase_price', 'fipe_reference_value'):
            value = resolve(field_name)
            if value is not None and value < 0:
                raise serializers.ValidationError(
                    {field_name: f'{field_name} não pode ser negativo.'}
                )

        return attrs


class VehicleExpenseSerializer(serializers.ModelSerializer):
    """Leitura e escrita. deleted_at/deletion_reason ficam visíveis na
    saída (útil pra investigação — mesmo raciocínio do Admin no Prompt 11),
    mas nunca graváveis por aqui: soft delete tem seu próprio fluxo, nunca
    um PATCH direto nesses campos.

    vehicle também é somente leitura (Prompt 16): nunca vem do corpo da
    requisição, nem na criação nem na edição — sempre vem da URL
    (/api/vehicles/{vehicle_id}/expenses/ na criação; a despesa já sabe seu
    vehicle na edição). A view de criação aninhada injeta o valor via
    serializer.save(vehicle=...), o jeito sancionado do DRF pra campo
    determinado pelo contexto da requisição em vez do payload do cliente —
    isso funciona mesmo com o campo marcado read_only aqui.

    Por que read_only (ignora silenciosamente) em vez de rejeitar com 400
    como asking_price/sale_price (Prompt 15)? São categorias diferentes:
    vehicle é um campo de ROTEAMENTO — em qualquer variação deste endpoint,
    ele sempre vem da URL, nunca do corpo; nenhum cliente razoável esperaria
    que reenviar o vehicle já presente na URL/no GET fizesse diferença.
    asking_price/sale_price são campos normalmente GRAVÁVEIS em outro
    caminho (endpoints do Prompt 17) e só ficam bloqueados aqui por regra de
    negócio — por isso merecem erro alto, senão o cliente pode achar que o
    preço mudou quando na verdade não mudou. Mesmo raciocínio aplicado a
    VehiclePhotoSerializer/VehiclePhotoUpdateSerializer (Prompt 18): lá,
    vehicle também é só ignorado, mas image (que É gravável no POST de
    criação) é rejeitado explicitamente quando presente no PATCH.
    """

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
        read_only_fields = [
            'id',
            'vehicle',
            'deleted_at',
            'deletion_reason',
            'created_at',
            'updated_at',
        ]


class VehiclePriceUpdateSerializer(serializers.Serializer):
    """Input de POST /api/vehicles/{id}/price/ (Prompt 17) — não é
    ModelSerializer de Vehicle de propósito: new_price/reason são a entrada
    da ação, não um mapeamento 1:1 de campos graváveis do model. A view é
    quem decide o que fazer com esses dados (criar o log, atualizar
    asking_price) — não reusa VehicleWriteSerializer, que rejeitaria
    justamente o campo que este endpoint existe pra escrever."""

    new_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0'))
    reason = serializers.CharField(allow_blank=False)


class VehicleSaleSerializer(serializers.Serializer):
    """Input de POST /api/vehicles/{id}/sale/ (Prompt 17) — mesma lógica do
    VehiclePriceUpdateSerializer acima: serializer de ação, não de Vehicle.

    Precisa do vehicle no context (`context={'vehicle': vehicle}`) pra
    validar sale_date >= purchase_date."""

    sale_price = serializers.DecimalField(max_digits=14, decimal_places=2)
    sale_date = serializers.DateField()
    reason = serializers.CharField(allow_blank=False)

    def validate_sale_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('sale_price deve ser maior que zero.')
        return value

    def validate(self, attrs):
        vehicle = self.context['vehicle']
        if attrs['sale_date'] < vehicle.purchase_date:
            raise serializers.ValidationError(
                {'sale_date': 'sale_date não pode ser anterior a purchase_date.'}
            )
        return attrs


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
    model (Prompt 10) — nunca aceito como entrada.

    vehicle também é somente leitura (mesmo padrão do Prompt 16 pra
    VehicleExpense): nunca vem do corpo, sempre da URL — injetado
    explicitamente via serializer.save(vehicle=...) na view de criação
    aninhada. PATCH (troca de capa/reordenação) não deveria poder mover uma
    foto pra outro veículo por engano de payload, então fica bloqueado
    também na edição.

    vehicle fica em read_only (ignorado silenciosamente), não numa rejeição
    de 400 — é um campo de ROTEAMENTO, sempre vindo da URL em qualquer
    variação deste endpoint, nunca um valor que o cliente teria motivo pra
    achar que está gravando. Comparar com VehiclePhotoUpdateSerializer.image
    abaixo: image É gravável no POST de criação, só fica bloqueado no PATCH
    por regra de negócio — por isso esse sim é rejeitado explicitamente,
    mesmo padrão de asking_price/sale_price (Prompt 15)."""

    class Meta:
        model = VehiclePhoto
        fields = ['id', 'vehicle', 'image', 'thumbnail', 'position', 'is_cover', 'created_at']
        read_only_fields = ['id', 'vehicle', 'thumbnail', 'created_at']


class VehiclePhotoUpdateSerializer(VehiclePhotoSerializer):
    """PATCH /api/photos/{id}/ (Prompt 18) — só aceita position e/ou
    is_cover de fato; vehicle continua read_only (herdado da classe base,
    ver justificativa lá) e image é rejeitado explicitamente — ver
    validate() abaixo.

    image não é editável por aqui: _process_image() (remoção de EXIF +
    geração de thumbnail, Prompt 10) só roda no save() de CRIAÇÃO
    (self._state.adding é True só nesse momento) — trocar a imagem via
    PATCH deixaria o thumbnail e o EXIF dessincronizados do arquivo novo,
    sem ninguém percebendo. Reenviar uma foto é um POST novo (cria outro
    registro), não uma edição do existente.

    Diferente de vehicle (campo de roteamento, sempre ignorado
    silenciosamente — ver VehiclePhotoSerializer acima), image É um campo
    normalmente gravável (no POST de criação) só bloqueado NESTE caminho
    por integridade de dados — a mesma categoria de asking_price/sale_price
    no VehicleWriteSerializer (Prompt 15). Por isso, ao contrário de
    vehicle, image presente no payload de PATCH é rejeitado com 400
    explícito, não silenciosamente ignorado: um cliente pode legitimamente
    achar que enviar image troca a foto, e uma falha silenciosa deixaria
    essa expectativa quebrada sem aviso."""

    NEVER_WRITABLE_ON_PATCH = {'image'}

    class Meta(VehiclePhotoSerializer.Meta):
        pass

    def validate(self, attrs):
        blocked_present = self.NEVER_WRITABLE_ON_PATCH & set(attrs.keys())
        if blocked_present:
            raise serializers.ValidationError({
                field_name: (
                    'Não é possível trocar a imagem por aqui. Envie uma nova '
                    'foto via POST /api/vehicles/{vehicle_id}/photos/ em vez '
                    'de editar esta.'
                )
                for field_name in sorted(blocked_present)
            })
        return attrs
