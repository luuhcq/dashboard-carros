from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from .filters import VehicleFilter
from .models import (
    Vehicle,
    VehicleExpense,
    VehiclePhoto,
    VehicleStatus,
    VehicleValueChangeLog,
    ValueChangeField,
)
from .querysets import annotate_vehicle_metrics
from .serializers import (
    VehicleDetailSerializer,
    VehicleExpenseSerializer,
    VehicleListSerializer,
    VehiclePhotoSerializer,
    VehiclePhotoUpdateSerializer,
    VehiclePriceUpdateSerializer,
    VehicleSaleSerializer,
    VehicleValueChangeLogSerializer,
    VehicleWriteSerializer,
)


def _soft_delete_or_400(request, instance, required_field_message):
    """Compartilhado entre Vehicle e VehicleExpense — mesma regra de soft
    delete exigindo deletion_reason (Prompt 15/16). Retorna a Response de
    erro se deletion_reason não veio no corpo; senão aplica o soft delete e
    retorna None (chamador decide a Response de sucesso)."""
    deletion_reason = request.data.get('deletion_reason')
    if not deletion_reason:
        return Response(
            {'deletion_reason': [required_field_message]}, status=status.HTTP_400_BAD_REQUEST
        )
    instance.deleted_at = timezone.now()
    instance.deletion_reason = deletion_reason
    instance.save()
    return None


class VehicleViewSet(viewsets.ModelViewSet):
    """CRUD de Vehicle. Autenticação: nenhum permission_classes é definido
    aqui de propósito — herda IsAuthenticated do DEFAULT_PERMISSION_CLASSES
    global (Prompt 04); não precisa de trabalho extra, só confirmar (ver
    testes) que continua valendo.

    Só PATCH é permitido pra update (sem PUT) — não foi pedido update total,
    só parcial.

    queryset usa Vehicle.objects (manager com soft delete, Prompt 06) — um
    veículo soft-deletado já some de list/retrieve/patch/delete
    automaticamente por causa disso, sem precisar de filtro extra aqui.
    """

    queryset = Vehicle.objects.all().order_by('-created_at')
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = VehicleFilter
    search_fields = ['internal_code', 'brand', 'model', 'version', 'plate']
    ordering_fields = [
        'purchase_date',
        'purchase_price',
        'total_cost',
        'asking_price',
        'days_in_stock',
        'margin',
        'roi',
        'model',
    ]

    def get_queryset(self):
        """Sempre anotado (Prompt 19), não só pra list(): get_object() (usado
        por retrieve/patch/delete) também passa pelos mesmos filter_backends
        acima — se a annotation fosse condicional só a 'list', um ordering=
        ou filtro na query string de um PATCH, por exemplo, quebraria com
        FieldError por referenciar uma coluna anotada inexistente. O custo
        extra de anotar pra uma busca de linha única é desprezível.

        select_related('company') evita uma query extra por linha se/quando
        o campo company for exposto num serializer — hoje nenhum dos dois
        (list/detail) usa, mas está aqui porque não custa nada continuar sem
        uso e resolve na hora se algum serializer futuro passar a expor
        company.
        """
        queryset = Vehicle.objects.select_related('company').order_by('-created_at')
        return annotate_vehicle_metrics(queryset)

    def get_serializer_class(self):
        if self.action == 'list':
            return VehicleListSerializer
        if self.action == 'retrieve':
            return VehicleDetailSerializer
        return VehicleWriteSerializer

    def destroy(self, request, *args, **kwargs):
        """Soft delete — nunca remove fisicamente. Exige deletion_reason no
        corpo da requisição; sem ele, 400 (nada é alterado)."""
        instance = self.get_object()
        error_response = _soft_delete_or_400(
            request, instance, 'Este campo é obrigatório para excluir um veículo.'
        )
        if error_response is not None:
            return error_response
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=VehiclePriceUpdateSerializer,
        responses={200: VehicleDetailSerializer},
        description=(
            'Único caminho autorizado para definir/alterar asking_price. Registra '
            'a mudança em VehicleValueChangeLog com o motivo informado antes de '
            'gravar o novo valor.'
        ),
    )
    @action(detail=True, methods=['post'], url_path='price')
    def price(self, request, pk=None):
        """POST /api/vehicles/{id}/price/ — único caminho autorizado pra
        definir/alterar asking_price (Prompt 15 bloqueia em qualquer outro
        lugar). Atualiza Vehicle.asking_price diretamente — não usa
        VehicleWriteSerializer, que rejeitaria esse campo de propósito."""
        vehicle = self.get_object()
        serializer = VehiclePriceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_price = serializer.validated_data['new_price']
        reason = serializer.validated_data['reason']

        with transaction.atomic():
            VehicleValueChangeLog.objects.create(
                vehicle=vehicle,
                field_name=ValueChangeField.ASKING_PRICE,
                old_value=vehicle.asking_price,
                new_value=new_price,
                reason=reason,
            )
            vehicle.asking_price = new_price
            vehicle.save()

        return Response(VehicleDetailSerializer(vehicle).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=VehicleSaleSerializer,
        responses={200: VehicleDetailSerializer},
        description=(
            'Único caminho autorizado para definir/corrigir sale_price e transicionar '
            'status para SOLD. Reusar num veículo já SOLD é o fluxo de correção de '
            'venda: um novo VehicleValueChangeLog é sempre criado, nunca editando o '
            'anterior.'
        ),
    )
    @action(detail=True, methods=['post'], url_path='sale')
    def sale(self, request, pk=None):
        """POST /api/vehicles/{id}/sale/ — único caminho autorizado pra
        definir/corrigir sale_price e transicionar status para SOLD. Reusar
        esta mesma ação num veículo já SOLD é o fluxo de correção de venda:
        nenhuma lógica especial pra isso — old_value só reflete o
        sale_price atual (que pode já não ser None), e um novo log é
        sempre criado, nunca editando o anterior."""
        vehicle = self.get_object()
        serializer = VehicleSaleSerializer(data=request.data, context={'vehicle': vehicle})
        serializer.is_valid(raise_exception=True)

        sale_price = serializer.validated_data['sale_price']
        sale_date = serializer.validated_data['sale_date']
        reason = serializer.validated_data['reason']

        with transaction.atomic():
            VehicleValueChangeLog.objects.create(
                vehicle=vehicle,
                field_name=ValueChangeField.SALE_PRICE,
                old_value=vehicle.sale_price,
                new_value=sale_price,
                reason=reason,
            )
            vehicle.sale_price = sale_price
            vehicle.sale_date = sale_date
            vehicle.status = VehicleStatus.SOLD
            vehicle.save()

        return Response(VehicleDetailSerializer(vehicle).data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: VehicleValueChangeLogSerializer(many=True)},
        description=(
            'Histórico completo de alterações de asking_price e sale_price do '
            'veículo (um registro por chamada de /price/ ou /sale/), mais recente '
            'primeiro.'
        ),
    )
    @action(detail=True, methods=['get'], url_path='value-changes')
    def value_changes(self, request, pk=None):
        """GET /api/vehicles/{id}/value-changes/ — histórico completo
        (asking_price e sale_price juntos), mais recente primeiro (ordering
        já definido em VehicleValueChangeLog.Meta)."""
        vehicle = self.get_object()
        logs = VehicleValueChangeLog.objects.filter(vehicle=vehicle)
        serializer = VehicleValueChangeLogSerializer(logs, many=True)
        return Response(serializer.data)


class VehicleExpenseListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/vehicles/{vehicle_id}/expenses/ — aninhado no veículo.

    vehicle nunca vem do corpo (serializer trata como read_only, Prompt 16)
    — sempre vem do vehicle_id da URL, injetado explicitamente em
    perform_create() via serializer.save(vehicle=...).
    """

    serializer_class = VehicleExpenseSerializer

    def get_vehicle(self):
        # Vehicle.objects já exclui soft-deletados — 404 automático tanto
        # pra veículo inexistente quanto pra soft-deletado, sem lógica extra.
        #
        # get_object_or_404 é o do rest_framework.generics, não o do django.
        # shortcuts (Prompt 23, achado na auditoria de formato de erro): a
        # versão do Django só converte DoesNotExist em Http404 — um
        # vehicle_id malformado (não-UUID) levanta ValidationError direto do
        # UUIDField, que escapava sem tratamento (500). A versão do DRF
        # também captura (TypeError, ValueError, ValidationError) e converte
        # pra Http404, que o exception_handler do DRF já sabe formatar como
        # JSON — mesmo comportamento que GenericAPIView.get_object() já dá
        # de graça pras rotas do router (vehicles/{pk}/, /price/, /sale/).
        return get_object_or_404(Vehicle.objects.all(), pk=self.kwargs['vehicle_id'])

    def get_queryset(self):
        # swagger_fake_view: geração de schema instancia a view sem
        # vehicle_id de verdade na URL — sem essa checagem, get_vehicle()
        # levanta KeyError e o drf-spectacular não consegue introspectar
        # o queryset (só usado pra inferir o Model, não pra listar nada).
        if getattr(self, 'swagger_fake_view', False):
            return VehicleExpense.objects.none()
        vehicle = self.get_vehicle()
        return VehicleExpense.objects.filter(vehicle=vehicle)

    def perform_create(self, serializer):
        vehicle = self.get_vehicle()
        serializer.save(vehicle=vehicle)


class VehicleExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH/DELETE /api/expenses/{expense_id}/ — rota independente (não
    aninhada): editar/excluir uma despesa não precisa do contexto do
    veículo na URL, a despesa já sabe o seu."""

    queryset = VehicleExpense.objects.all()
    serializer_class = VehicleExpenseSerializer
    lookup_url_kwarg = 'expense_id'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        error_response = _soft_delete_or_400(
            request, instance, 'Este campo é obrigatório para excluir uma despesa.'
        )
        if error_response is not None:
            return error_response
        return Response(status=status.HTTP_204_NO_CONTENT)


class VehiclePhotoListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/vehicles/{vehicle_id}/photos/ — aninhado, mesmo padrão
    de VehicleExpenseListCreateView (Prompt 16): vehicle nunca vem do
    corpo, sempre da URL. Ordenação por position já vem do Meta.ordering
    de VehiclePhoto — não precisa de order_by aqui."""

    serializer_class = VehiclePhotoSerializer

    def get_vehicle(self):
        return get_object_or_404(Vehicle.objects.all(), pk=self.kwargs['vehicle_id'])

    def get_queryset(self):
        # swagger_fake_view: mesmo motivo do VehicleExpenseListCreateView
        # acima — geração de schema não tem vehicle_id de verdade na URL.
        if getattr(self, 'swagger_fake_view', False):
            return VehiclePhoto.objects.none()
        vehicle = self.get_vehicle()
        return VehiclePhoto.objects.filter(vehicle=vehicle)

    def perform_create(self, serializer):
        vehicle = self.get_vehicle()
        serializer.save(vehicle=vehicle)


class VehiclePhotoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH/DELETE /api/photos/{id}/ — rota independente (não aninhada).

    PATCH usa VehiclePhotoUpdateSerializer (só position/is_cover) — a troca
    de capa reusa a lógica atômica já em VehiclePhoto.save() (Prompt 10),
    nada duplicado aqui.

    DELETE: nenhum destroy() customizado — o mixin padrão do DRF já chama
    instance.delete(), e VehiclePhoto.delete() (Prompt 18) já cuida de
    remover os arquivos físicos do storage. Diferente de Vehicle/
    VehicleExpense, não há soft delete nem deletion_reason aqui (decisão
    documentada no model: fotos não têm valor de auditoria como preço/venda
    têm)."""

    queryset = VehiclePhoto.objects.all()
    serializer_class = VehiclePhotoUpdateSerializer
    lookup_url_kwarg = 'photo_id'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
