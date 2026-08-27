from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Company
from vehicles.models import Vehicle, VehicleStatus


def make_vehicle(company, **overrides):
    defaults = {
        'company': company,
        'brand': 'Marca',
        'model': 'Modelo',
        'purchase_date': date(2026, 1, 1),
        'purchase_price': Decimal('50000.00'),
    }
    defaults.update(overrides)
    return Vehicle.objects.create(**defaults)


class AuthenticatedAPITestCase(APITestCase):
    """Base com login real via /api/auth/login/ — o cookie JWT fica no
    client, então as requisições seguintes já chegam autenticadas, do jeito
    que a API de verdade funciona (cookie httpOnly, não header)."""

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

    def list_url(self):
        return reverse('vehicle-list')

    def detail_url(self, vehicle):
        return reverse('vehicle-detail', kwargs={'pk': vehicle.pk})


class VehicleUnauthenticatedAccessTests(APITestCase):
    """Confirma explicitamente (não assume) que IsAuthenticated (Prompt 04)
    está valendo em todos os métodos deste endpoint, sem trabalho extra
    nosso — nenhum permission_classes foi setado no ViewSet."""

    def setUp(self):
        company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(company)

    def test_list_requires_authentication(self):
        response = self.client.get(reverse('vehicle-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        response = self.client.post(reverse('vehicle-list'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_authentication(self):
        url = reverse('vehicle-detail', kwargs={'pk': self.vehicle.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_requires_authentication(self):
        url = reverse('vehicle-detail', kwargs={'pk': self.vehicle.pk})
        response = self.client.patch(url, {'notes': 'x'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_requires_authentication(self):
        url = reverse('vehicle-detail', kwargs={'pk': self.vehicle.pk})
        response = self.client.delete(url, {'deletion_reason': 'x'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class VehicleCreateTests(AuthenticatedAPITestCase):
    def _valid_payload(self, **overrides):
        payload = {
            'company': str(self.company.id),
            'brand': 'Toyota',
            'model': 'Corolla',
            'purchase_date': '2026-01-10',
            'purchase_price': '80000.00',
        }
        payload.update(overrides)
        return payload

    def test_create_with_valid_data_succeeds(self):
        response = self.client.post(self.list_url(), self._valid_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['brand'], 'Toyota')
        self.assertTrue(response.data['internal_code'])  # gerado automaticamente
        self.assertEqual(Vehicle.objects.count(), 1)

    def test_create_without_company_field_succeeds_and_auto_assigns_company(self):
        """company é read_only (Prompt 30) — não há endpoint pra um client
        comum descobrir um UUID de Company, então o campo nem precisa vir
        no payload. VehicleViewSet.perform_create() injeta a Company mais
        antiga (a semeada por core/migrations/0002_seed_initial_company.py,
        que já existe na base de teste antes de qualquer setUp rodar)."""
        payload = self._valid_payload()
        del payload['company']
        response = self.client.post(self.list_url(), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        vehicle = Vehicle.objects.get(id=response.data['id'])
        self.assertEqual(vehicle.company.name, 'Revenda Principal')

    def test_create_ignores_company_sent_by_client(self):
        """company sendo read_only, um UUID mandado no payload é
        silenciosamente ignorado pelo DRF (não vira erro, não é usado) — a
        Company usada continua sendo a injetada por perform_create(), nunca
        a do client."""
        response = self.client.post(self.list_url(), self._valid_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        vehicle = Vehicle.objects.get(id=response.data['id'])
        self.assertNotEqual(vehicle.company_id, self.company.id)
        self.assertEqual(vehicle.company.name, 'Revenda Principal')

    def test_create_missing_brand_is_rejected(self):
        payload = self._valid_payload()
        del payload['brand']
        response = self.client.post(self.list_url(), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('brand', response.data)
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_create_missing_model_is_rejected(self):
        payload = self._valid_payload()
        del payload['model']
        response = self.client.post(self.list_url(), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('model', response.data)
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_create_missing_purchase_date_is_rejected(self):
        payload = self._valid_payload()
        del payload['purchase_date']
        response = self.client.post(self.list_url(), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('purchase_date', response.data)
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_create_missing_purchase_price_is_rejected(self):
        payload = self._valid_payload()
        del payload['purchase_price']
        response = self.client.post(self.list_url(), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('purchase_price', response.data)
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_create_rejects_asking_price_same_as_patch(self):
        """asking_price/sale_price nunca são graváveis por este endpoint,
        nem na criação — não existe "primeira definição sem valor anterior"
        que valha aqui; isso só acontece pelos endpoints dedicados do
        Prompt 17. Mesma checagem e mesma mensagem usadas no PATCH."""
        response = self.client.post(
            self.list_url(), self._valid_payload(asking_price='95000.00'), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('asking_price', response.data)
        self.assertIn('Prompt 17', response.data['asking_price'][0])
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_create_rejects_sale_price_same_as_patch(self):
        response = self.client.post(
            self.list_url(), self._valid_payload(sale_price='90000.00'), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sale_price', response.data)
        self.assertIn('Prompt 17', response.data['sale_price'][0])
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_create_rejects_both_asking_price_and_sale_price_together(self):
        response = self.client.post(
            self.list_url(),
            self._valid_payload(asking_price='95000.00', sale_price='90000.00'),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('asking_price', response.data)
        self.assertIn('sale_price', response.data)
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_create_rejects_sale_date_before_purchase_date(self):
        """sale_date continua gravável na criação (só asking_price/sale_price
        são bloqueados) — não inclui sale_price no payload de propósito, pra
        isolar exatamente a regra sendo testada aqui."""
        response = self.client.post(
            self.list_url(),
            self._valid_payload(sale_date='2026-01-05'),  # antes de purchase_date=2026-01-10
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sale_date', response.data)
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_create_rejects_negative_purchase_price(self):
        response = self.client.post(
            self.list_url(), self._valid_payload(purchase_price='-1.00'), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('purchase_price', response.data)

    def test_create_rejects_negative_mileage(self):
        """mileage >= 0 já vem do PositiveIntegerField do model — confirma
        que o validador automático do DRF pra esse tipo de campo está
        realmente ativo, não só assumido."""
        response = self.client.post(
            self.list_url(), self._valid_payload(mileage=-100), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mileage', response.data)


class VehicleListDetailTests(AuthenticatedAPITestCase):
    def test_list_uses_summary_serializer_fields(self):
        make_vehicle(self.company, asking_price=Decimal('60000.00'))
        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        row = response.data[0]
        self.assertNotIn('metrics', row)  # é o serializer resumido, não o de detalhe
        self.assertIn('total_cost', row)
        self.assertIn('margin', row)
        self.assertIn('aging_bucket', row)
        self.assertIn('days_in_stock', row)

    def test_retrieve_uses_detail_serializer_with_metrics(self):
        vehicle = make_vehicle(self.company, asking_price=Decimal('60000.00'))
        response = self.client.get(self.detail_url(vehicle))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('metrics', response.data)
        self.assertIn('total_cost', response.data['metrics'])
        self.assertEqual(len(response.data['metrics']), 13)


class VehiclePatchTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.vehicle = make_vehicle(
            self.company, purchase_price=Decimal('50000.00'), asking_price=Decimal('60000.00')
        )

    def test_patch_common_field_succeeds(self):
        response = self.client.patch(
            self.detail_url(self.vehicle), {'notes': 'Revisado e pronto'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.notes, 'Revisado e pronto')

    def test_patch_asking_price_alone_is_rejected(self):
        response = self.client.patch(
            self.detail_url(self.vehicle), {'asking_price': '70000.00'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('asking_price', response.data)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.asking_price, Decimal('60000.00'))  # não mudou

    def test_patch_sale_price_alone_is_rejected(self):
        response = self.client.patch(
            self.detail_url(self.vehicle), {'sale_price': '55000.00'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sale_price', response.data)
        self.vehicle.refresh_from_db()
        self.assertIsNone(self.vehicle.sale_price)

    def test_patch_with_forbidden_field_alongside_valid_field_rejects_everything(self):
        """Decisão confirmada com o usuário: rejeição total, nada é
        persistido — nem o campo válido do mesmo payload."""
        response = self.client.patch(
            self.detail_url(self.vehicle),
            {'notes': 'não deveria ser salvo', 'asking_price': '99999.00'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.vehicle.refresh_from_db()
        self.assertIsNone(self.vehicle.notes)  # o campo válido TAMBÉM não foi aplicado
        self.assertEqual(self.vehicle.asking_price, Decimal('60000.00'))

    def test_patch_cannot_edit_internal_code(self):
        original_code = self.vehicle.internal_code
        response = self.client.patch(
            self.detail_url(self.vehicle), {'internal_code': 'CAR-999999'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.internal_code, original_code)


class VehicleDeleteTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.vehicle = make_vehicle(self.company)

    def test_delete_without_deletion_reason_is_rejected(self):
        response = self.client.delete(self.detail_url(self.vehicle), {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('deletion_reason', response.data)

        self.vehicle.refresh_from_db()
        self.assertIsNone(self.vehicle.deleted_at)
        self.assertEqual(Vehicle.objects.count(), 1)

    def test_delete_with_deletion_reason_soft_deletes(self):
        response = self.client.delete(
            self.detail_url(self.vehicle),
            {'deletion_reason': 'Cadastrado por engano'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.vehicle.refresh_from_db()
        self.assertIsNotNone(self.vehicle.deleted_at)
        self.assertEqual(self.vehicle.deletion_reason, 'Cadastrado por engano')

        # segue no banco (soft delete, não hard delete)
        self.assertTrue(Vehicle.all_objects.filter(pk=self.vehicle.pk).exists())

        # mas some da listagem normal
        list_response = self.client.get(self.list_url())
        ids_in_list = [row['id'] for row in list_response.data]
        self.assertNotIn(str(self.vehicle.pk), ids_in_list)

    def test_delete_never_hard_deletes(self):
        vehicle_pk = self.vehicle.pk
        self.client.delete(
            self.detail_url(self.vehicle), {'deletion_reason': 'teste'}, format='json'
        )
        self.assertTrue(Vehicle.all_objects.filter(pk=vehicle_pk).exists())
