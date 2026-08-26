"""Testes de integração genuinamente novos (Prompt 21) — jornadas que
atravessam múltiplos prompts numa sequência que nenhum teste existente
cobre de ponta a ponta. Cada um documenta explicitamente por que não
duplica cobertura já existente (checagem feita por busca textual antes de
escrever qualquer teste novo, mesmo padrão dos prompts anteriores)."""

import os
import tempfile
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Company
from vehicles.models import ExpenseCategory, Vehicle, VehiclePhoto, VehicleStatus, VehicleValueChangeLog
from vehicles.test_photo_views import make_uploaded_image


class AuthenticatedAPITestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='revenda', password='S3nhaForte!23'
        )
        response = self.client.post(
            reverse('auth-login'),
            {'username': 'revenda', 'password': 'S3nhaForte!23'},
            format='json',
        )
        assert response.status_code == 200, response.data
        self.company = Company.objects.create(name='Empresa de teste')


class FullVehicleLifecycleJourneyTests(AuthenticatedAPITestCase):
    """Jornada completa: criação -> despesas (uma soft-deletada) -> preço
    definido duas vezes -> venda -> correção de venda -> soft delete do
    veículo -> confirma sumiço de listagem/dashboard mas acesso continuado
    via all_objects/Admin/log de auditoria.

    Por que é novo, não duplicado: o teste mais próximo que já existe é
    ExpenseAffectsVehicleTotalCostEndToEndTests (Prompt 16), que só cobre
    criação -> 1 despesa -> total_cost via detalhe -> soft-delete da
    despesa -> total_cost de novo. Não toca preço, venda, correção de
    venda, nem soft delete do PRÓPRIO veículo, nem dashboard. O cenário de
    preço/venda mais completo (Prompt 17) para no histórico de
    value-changes — não continua pra soft delete do veículo nem verifica
    reflexo no dashboard ou consistência entre listagem/detalhe/dashboard
    pra o mesmo veículo. Essa consistência cruzada (list annotate() do
    Prompt 19 vs. detail via VehicleMetricsService do Prompt 12 vs.
    agregado do dashboard do Prompt 20, todos concordando pros MESMOS
    dados, através da API de verdade) nunca foi verificada em conjunto.
    """

    def test_full_lifecycle_from_creation_to_soft_delete(self):
        today = date.today()

        # === 1) Criação (Prompt 06/07/15) ===
        create_response = self.client.post(
            reverse('vehicle-list'),
            {
                'company': str(self.company.id),
                'brand': 'Honda',
                'model': 'Civic',
                'purchase_date': today.isoformat(),
                'purchase_price': '45000.00',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)
        vehicle_id = create_response.data['id']
        self.assertTrue(create_response.data['internal_code'])

        list_response = self.client.get(reverse('vehicle-list'))
        self.assertIn(vehicle_id, [row['id'] for row in list_response.data])

        # === 2) Duas despesas, uma soft-deletada depois (Prompt 08/16) ===
        expense1 = self.client.post(
            reverse('vehicle-expense-list', kwargs={'vehicle_id': vehicle_id}),
            {
                'date': today.isoformat(), 'category': ExpenseCategory.MECHANICAL,
                'description': 'Revisão', 'amount': '1200.00',
            },
            format='json',
        ).data
        expense2 = self.client.post(
            reverse('vehicle-expense-list', kwargs={'vehicle_id': vehicle_id}),
            {
                'date': today.isoformat(), 'category': ExpenseCategory.DETAILING,
                'description': 'Higienização', 'amount': '300.00',
            },
            format='json',
        ).data

        detail_response = self.client.get(reverse('vehicle-detail', kwargs={'pk': vehicle_id}))
        self.assertEqual(detail_response.data['metrics']['total_cost'], '46500.00')  # 45000+1200+300

        delete_expense_response = self.client.delete(
            reverse('expense-detail', kwargs={'expense_id': expense2['id']}),
            {'deletion_reason': 'Lançamento duplicado'},
            format='json',
        )
        self.assertEqual(delete_expense_response.status_code, status.HTTP_204_NO_CONTENT)

        detail_response = self.client.get(reverse('vehicle-detail', kwargs={'pk': vehicle_id}))
        self.assertEqual(detail_response.data['metrics']['total_cost'], '46200.00')  # 45000+1200

        # CROSS-CHECK: listagem (annotate() em SQL, Prompt 19) e detalhe
        # (VehicleMetricsService em Python, Prompt 12) precisam concordar
        # pro MESMO veículo — nunca comparados via API antes.
        list_response = self.client.get(reverse('vehicle-list'))
        list_row = next(row for row in list_response.data if row['id'] == vehicle_id)
        self.assertEqual(list_row['total_cost'], detail_response.data['metrics']['total_cost'])

        # e o dashboard (Prompt 20) também precisa refletir o mesmo total,
        # já que só existe esse veículo na base neste teste
        summary_response = self.client.get(reverse('dashboard-summary'))
        self.assertEqual(summary_response.data['vehicles_in_stock'], 1)
        self.assertEqual(summary_response.data['capital_employed'], '46200.00')

        # === 3) Preço definido duas vezes (Prompt 17) ===
        self.client.post(
            reverse('vehicle-price', kwargs={'pk': vehicle_id}),
            {'new_price': '55000.00', 'reason': 'Preço inicial'},
            format='json',
        )
        self.client.post(
            reverse('vehicle-price', kwargs={'pk': vehicle_id}),
            {'new_price': '52000.00', 'reason': 'Ajuste'},
            format='json',
        )
        price_logs = VehicleValueChangeLog.objects.filter(
            vehicle_id=vehicle_id, field_name='asking_price'
        ).order_by('changed_at')
        self.assertEqual(price_logs.count(), 2)
        self.assertIsNone(price_logs.first().old_value)
        self.assertEqual(price_logs.last().old_value, Decimal('55000.00'))

        # antes de vender, o veículo conta no dashboard como em estoque
        summary_response = self.client.get(reverse('dashboard-summary'))
        self.assertEqual(summary_response.data['vehicles_in_stock'], 1)

        # === 4) Venda (Prompt 17) ===
        sale_response = self.client.post(
            reverse('vehicle-sale', kwargs={'pk': vehicle_id}),
            {'sale_price': '51000.00', 'sale_date': today.isoformat(), 'reason': 'Venda concluída'},
            format='json',
        )
        self.assertEqual(sale_response.status_code, status.HTTP_200_OK, sale_response.data)
        self.assertEqual(sale_response.data['status'], VehicleStatus.SOLD)

        # depois de vendido, some do "em estoque" do dashboard (summary/aging
        # excluem SOLD por definição, Prompt 20), mas aparece no status/
        status_response = self.client.get(reverse('dashboard-status'))
        self.assertEqual(status_response.data['SOLD'], 1)
        summary_response = self.client.get(reverse('dashboard-summary'))
        self.assertEqual(summary_response.data['vehicles_in_stock'], 0)

        # === 5) Correção de venda (Prompt 17) — mesmo endpoint, novo log ===
        correction_response = self.client.post(
            reverse('vehicle-sale', kwargs={'pk': vehicle_id}),
            {
                'sale_price': '49500.00', 'sale_date': today.isoformat(),
                'reason': 'Desconto concedido no fechamento',
            },
            format='json',
        )
        self.assertEqual(correction_response.status_code, status.HTTP_200_OK)

        sale_logs = VehicleValueChangeLog.objects.filter(
            vehicle_id=vehicle_id, field_name='sale_price'
        ).order_by('changed_at')
        self.assertEqual(sale_logs.count(), 2)
        self.assertEqual(sale_logs.first().new_value, Decimal('51000.00'))  # log antigo intacto
        self.assertEqual(sale_logs.last().old_value, Decimal('51000.00'))
        self.assertEqual(sale_logs.last().new_value, Decimal('49500.00'))

        # === 6) Soft delete do veículo com justificativa (Prompt 15) ===
        delete_response = self.client.delete(
            reverse('vehicle-detail', kwargs={'pk': vehicle_id}),
            {'deletion_reason': 'Veículo devolvido ao fornecedor após a venda'},
            format='json',
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # some da listagem normal
        list_response = self.client.get(reverse('vehicle-list'))
        self.assertNotIn(vehicle_id, [row['id'] for row in list_response.data])

        # some da contagem de status do dashboard também (mesmo manager)
        status_response = self.client.get(reverse('dashboard-status'))
        self.assertEqual(status_response.data['SOLD'], 0)

        # detalhe via API também não acha mais (manager exclui soft-deletado)
        detail_response = self.client.get(reverse('vehicle-detail', kwargs={'pk': vehicle_id}))
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

        # o histórico de preço/venda também fica inacessível por ESTE
        # caminho (a action depende de get_object() no veículo) — mas os
        # registros em si continuam intactos no banco, verificado direto
        value_changes_response = self.client.get(
            reverse('vehicle-value-changes', kwargs={'pk': vehicle_id})
        )
        self.assertEqual(value_changes_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            VehicleValueChangeLog.objects.filter(vehicle_id=vehicle_id).count(), 4
        )  # 2 de preço + 2 de venda, nenhum apagado

        # mas continua acessível via all_objects (Prompt 06) com os dados
        # de soft delete corretos
        vehicle = Vehicle.all_objects.get(pk=vehicle_id)
        self.assertIsNotNone(vehicle.deleted_at)
        self.assertEqual(
            vehicle.deletion_reason, 'Veículo devolvido ao fornecedor após a venda'
        )
        self.assertEqual(vehicle.status, VehicleStatus.SOLD)  # preservado

        # e continua visível no Admin (Prompt 11: all_objects + badge)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        admin_response = self.client.get('/admin/vehicles/vehicle/')
        self.assertContains(admin_response, vehicle.internal_code)
        self.assertContains(admin_response, 'Deletado')


class PhotoEndpointsAfterVehicleSoftDeleteTests(AuthenticatedAPITestCase):
    """Fotos (Prompt 10/18) não têm soft delete próprio, mas o veículo dono
    tem (Prompt 15) — essa interação nunca foi testada. VehicleExpense já
    tem esse teste (test_create_for_soft_deleted_vehicle_returns_404 /
    test_list_for_soft_deleted_vehicle_returns_404, Prompt 16), mas
    VehiclePhoto nunca ganhou o equivalente no Prompt 18 — confirmado por
    busca textual em test_photo_views.py antes de escrever isto."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root_dir = tempfile.TemporaryDirectory()
        cls._media_root_override = override_settings(MEDIA_ROOT=cls._media_root_dir.name)
        cls._media_root_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_root_override.disable()
        cls._media_root_dir.cleanup()
        super().tearDownClass()

    def test_photo_endpoints_404_after_vehicle_soft_delete_but_photos_and_files_survive(self):
        vehicle = Vehicle.objects.create(
            company=self.company, brand='Fiat', model='Argo',
            purchase_date=date.today(), purchase_price=Decimal('30000.00'),
        )
        photo = VehiclePhoto.objects.create(
            vehicle=vehicle, image=make_uploaded_image('capa.jpg'), is_cover=True
        )
        image_path = photo.image.path
        thumbnail_path = photo.thumbnail.path
        self.assertTrue(os.path.exists(image_path))

        # soft-deleta o veículo (Prompt 15)
        delete_response = self.client.delete(
            reverse('vehicle-detail', kwargs={'pk': vehicle.pk}),
            {'deletion_reason': 'teste de integração'},
            format='json',
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # GET/POST na rota aninhada (que depende de achar o veículo via
        # Vehicle.objects, que exclui soft-deletado) agora dão 404
        photos_url = reverse('vehicle-photo-list', kwargs={'vehicle_id': vehicle.pk})
        self.assertEqual(self.client.get(photos_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.post(
                photos_url, {'image': make_uploaded_image('nova.jpg')}, format='multipart'
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # mas a foto em si (registro E arquivo físico) não foi tocada —
        # VehiclePhoto não tem soft delete próprio nem é filtrada pelo
        # soft delete do veículo dono
        self.assertTrue(VehiclePhoto.objects.filter(pk=photo.pk).exists())
        self.assertTrue(os.path.exists(image_path))
        self.assertTrue(os.path.exists(thumbnail_path))

        # e a rota independente (Prompt 18: photo-detail não depende do
        # veículo estar visível) ainda funciona normalmente
        photo_detail_url = reverse('photo-detail', kwargs={'photo_id': photo.pk})
        get_response = self.client.get(photo_detail_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        delete_photo_response = self.client.delete(photo_detail_url)
        self.assertEqual(delete_photo_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VehiclePhoto.objects.filter(pk=photo.pk).exists())
        self.assertFalse(os.path.exists(image_path))  # hard delete removeu o arquivo de verdade
