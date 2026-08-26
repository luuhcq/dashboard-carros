from django.urls import path
from rest_framework.routers import DefaultRouter

from .dashboard_views import DashboardAgingView, DashboardStatusView, DashboardSummaryView
from .views import (
    VehicleExpenseDetailView,
    VehicleExpenseListCreateView,
    VehiclePhotoDetailView,
    VehiclePhotoListCreateView,
    VehicleViewSet,
)

router = DefaultRouter()
router.register('vehicles', VehicleViewSet, basename='vehicle')

urlpatterns = [
    # Paths explícitos primeiro: vehicles/<id>/expenses/ e vehicles/<id>/photos/
    # têm um segmento a mais que o vehicles/<pk>/ do router, então não
    # colidiriam de qualquer forma (o router é ancorado no fim), mas a ordem
    # deixa a intenção clara.
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
    path(
        'vehicles/<uuid:vehicle_id>/photos/',
        VehiclePhotoListCreateView.as_view(),
        name='vehicle-photo-list',
    ),
    path(
        'photos/<uuid:photo_id>/',
        VehiclePhotoDetailView.as_view(),
        name='photo-detail',
    ),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/aging/', DashboardAgingView.as_view(), name='dashboard-aging'),
    path('dashboard/status/', DashboardStatusView.as_view(), name='dashboard-status'),
] + router.urls
