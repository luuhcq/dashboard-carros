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
    #
    # <str:...>, não <uuid:...> (Prompt 23, achado na auditoria de formato de
    # erro): o converter <uuid:...> do Django só casa a URL se o segmento já
    # for um UUID sintaticamente válido — um id malformado nem chega a
    # resolver pra view nenhuma, e cai no 404 HTML padrão do Django (não
    # JSON), quebrando a promessa de formato de erro previsível pro
    # frontend. As rotas do router (vehicles/{pk}/, /price/, /sale/,
    # /value-changes/) nunca tiveram esse problema porque o router usa um
    # regex permissivo ([^/.]+) por padrão — o id malformado chega até a
    # view, que devolve 404 JSON de verdade via get_object_or_404 do DRF.
    # <str:...> aqui replica esse mesmo comportamento permissivo; quem
    # garante o 404 (em vez de 500) pro valor malformado dentro da view é o
    # get_object_or_404 do rest_framework.generics usado em
    # VehicleExpenseListCreateView/VehiclePhotoListCreateView.get_vehicle()
    # — ver comentário lá.
    path(
        'vehicles/<str:vehicle_id>/expenses/',
        VehicleExpenseListCreateView.as_view(),
        name='vehicle-expense-list',
    ),
    path(
        'expenses/<str:expense_id>/',
        VehicleExpenseDetailView.as_view(),
        name='expense-detail',
    ),
    path(
        'vehicles/<str:vehicle_id>/photos/',
        VehiclePhotoListCreateView.as_view(),
        name='vehicle-photo-list',
    ),
    path(
        'photos/<str:photo_id>/',
        VehiclePhotoDetailView.as_view(),
        name='photo-detail',
    ),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/aging/', DashboardAgingView.as_view(), name='dashboard-aging'),
    path('dashboard/status/', DashboardStatusView.as_view(), name='dashboard-status'),
] + router.urls
