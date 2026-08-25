from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Vehicle
from .serializers import VehicleDetailSerializer, VehicleListSerializer, VehicleWriteSerializer


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
        deletion_reason = request.data.get('deletion_reason')
        if not deletion_reason:
            return Response(
                {'deletion_reason': ['Este campo é obrigatório para excluir um veículo.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = self.get_object()
        instance.deleted_at = timezone.now()
        instance.deletion_reason = deletion_reason
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
