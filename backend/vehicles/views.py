from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.response import Response

from .models import Vehicle, VehicleExpense
from .serializers import (
    VehicleDetailSerializer,
    VehicleExpenseSerializer,
    VehicleListSerializer,
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
        return get_object_or_404(Vehicle.objects.all(), pk=self.kwargs['vehicle_id'])

    def get_queryset(self):
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
