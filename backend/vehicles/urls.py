from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import VehicleExpenseDetailView, VehicleExpenseListCreateView, VehicleViewSet

router = DefaultRouter()
router.register('vehicles', VehicleViewSet, basename='vehicle')

urlpatterns = [
    # Paths explícitos primeiro: vehicles/<id>/expenses/ tem um segmento a
    # mais que o vehicles/<pk>/ do router, então não colidiriam de qualquer
    # forma (o router é ancorado no fim), mas a ordem deixa a intenção clara.
    path(
        'vehicles/<uuid:vehicle_id>/expenses/',
        VehicleExpenseListCreateView.as_view(),
        name='vehicle-expense-list',
    ),
    path(
        'expenses/<uuid:expense_id>/',
        VehicleExpenseDetailView.as_view(),
        name='expense-detail',
    ),
] + router.urls
