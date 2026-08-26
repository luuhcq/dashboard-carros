import uuid
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Company
from vehicles.models import ExpenseCategory, Vehicle, VehicleExpense


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


def make_expense(vehicle, **overrides):
    defaults = {
        'vehicle': vehicle,
        'date': date(2026, 1, 15),
        'category': ExpenseCategory.MECHANICAL,
        'description': 'Troca de óleo',
        'amount': Decimal('350.00'),
    }
    defaults.update(overrides)
    return VehicleExpense.objects.create(**defaults)


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
        self.vehicle = make_vehicle(self.company)

    def expense_list_url(self, vehicle=None):
        vehicle = vehicle or self.vehicle
        return reverse('vehicle-expense-list', kwargs={'vehicle_id': vehicle.pk})

    def expense_detail_url(self, expense):
        return reverse('expense-detail', kwargs={'expense_id': expense.pk})

    def vehicle_detail_url(self, vehicle=None):
        vehicle = vehicle or self.vehicle
        return reverse('vehicle-detail', kwargs={'pk': vehicle.pk})


class ExpenseUnauthenticatedAccessTests(APITestCase):
    def setUp(self):
        company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(company)
        self.expense = make_expense(self.vehicle)

    def test_list_requires_authentication(self):
        url = reverse('vehicle-expense-list', kwargs={'vehicle_id': self.vehicle.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        url = reverse('vehicle-expense-list', kwargs={'vehicle_id': self.vehicle.pk})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_requires_authentication(self):
        url = reverse('expense-detail', kwargs={'expense_id': self.expense.pk})
        response = self.client.patch(url, {'notes': 'x'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_requires_authentication(self):
        url = reverse('expense-detail', kwargs={'expense_id': self.expense.pk})
        response = self.client.delete(url, {'deletion_reason': 'x'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_authentication(self):
        """expense-detail também aceita GET (RetrieveUpdateDestroyAPIView) —
        só PATCH/DELETE tinham teste de 401 (Prompt 21: revisão de cobertura
        encontrou essa lacuna)."""
        url = reverse('expense-detail', kwargs={'expense_id': self.expense.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ExpenseCreateTests(AuthenticatedAPITestCase):
    def _valid_payload(self, **overrides):
        payload = {
            'date': '2026-01-15',
            'category': ExpenseCategory.MECHANICAL,
            'description': 'Revisão geral',
            'amount': '350.00',
        }
        payload.update(overrides)
        return payload

    def test_create_links_expense_to_vehicle_from_url(self):
        response = self.client.post(
            self.expense_list_url(), self._valid_payload(), format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # response.data é a estrutura Python pré-render: o campo 'vehicle'
        # (PrimaryKeyRelatedField, FK) fica como UUID cru aqui, não string —
        # diferente de 'id' (UUIDField), que já stringifica em to_representation.
        # Confirmado empiricamente antes de escrever esta asserção.
        self.assertEqual(response.data['vehicle'], self.vehicle.pk)

        # no JSON de verdade que vai pro cliente, vira string (o encoder do
        # DRF stringifica UUID no render, igual faz com Decimal)
        rendered = self.client.get(self.expense_detail_url(
            VehicleExpense.objects.get(pk=response.data['id'])
        ))
        self.assertEqual(rendered.data['vehicle'], self.vehicle.pk)
        self.assertIn(
            f'"vehicle":"{self.vehicle.pk}"', rendered.content.decode().replace(' ', '')
        )

        expense = VehicleExpense.objects.get(pk=response.data['id'])
        self.assertEqual(expense.vehicle_id, self.vehicle.pk)

    def test_create_ignores_vehicle_in_body_uses_url_instead(self):
        """Não aceita vehicle no corpo — mesmo enviando o id de OUTRO
        veículo no payload, a despesa é vinculada ao vehicle_id da URL."""
        other_vehicle = make_vehicle(self.company, brand='Outro')

        response = self.client.post(
            self.expense_list_url(self.vehicle),
            self._valid_payload(vehicle=str(other_vehicle.pk)),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        expense = VehicleExpense.objects.get(pk=response.data['id'])
        self.assertEqual(expense.vehicle_id, self.vehicle.pk)  # da URL, não do body
        self.assertNotEqual(expense.vehicle_id, other_vehicle.pk)

    def test_create_for_nonexistent_vehicle_returns_404(self):
        random_id = uuid.uuid4()
        url = reverse('vehicle-expense-list', kwargs={'vehicle_id': random_id})

        response = self.client.post(url, self._valid_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(VehicleExpense.objects.count(), 0)

    def test_create_for_soft_deleted_vehicle_returns_404(self):
        self.vehicle.deleted_at = timezone.now()
        self.vehicle.deletion_reason = 'teste'
        self.vehicle.save()

        response = self.client.post(
            self.expense_list_url(self.vehicle), self._valid_payload(), format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_rejects_zero_amount(self):
        response = self.client.post(
            self.expense_list_url(), self._valid_payload(amount='0.00'), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)


class ExpenseListTests(AuthenticatedAPITestCase):
    def test_list_for_nonexistent_vehicle_returns_404(self):
        random_id = uuid.uuid4()
        url = reverse('vehicle-expense-list', kwargs={'vehicle_id': random_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_for_soft_deleted_vehicle_returns_404(self):
        self.vehicle.deleted_at = timezone.now()
        self.vehicle.save()

        response = self.client.get(self.expense_list_url(self.vehicle))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_returns_only_active_expenses_of_that_vehicle(self):
        other_vehicle = make_vehicle(self.company, brand='Outro')

        active = make_expense(self.vehicle, description='Ativa')
        deleted = make_expense(self.vehicle, description='Deletada')
        deleted.deleted_at = timezone.now()
        deleted.save()
        make_expense(other_vehicle, description='De outro veículo')

        response = self.client.get(self.expense_list_url(self.vehicle))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertEqual(ids, [str(active.pk)])


class ExpensePatchTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.expense = make_expense(self.vehicle)

    def test_patch_updates_expense(self):
        response = self.client.patch(
            self.expense_detail_url(self.expense),
            {'description': 'Revisão completa', 'amount': '400.00'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.description, 'Revisão completa')
        self.assertEqual(self.expense.amount, Decimal('400.00'))

    def test_patch_ignores_vehicle_field(self):
        other_vehicle = make_vehicle(self.company, brand='Outro')
        response = self.client.patch(
            self.expense_detail_url(self.expense),
            {'vehicle': str(other_vehicle.pk), 'description': 'Tentando trocar veículo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.vehicle_id, self.vehicle.pk)  # não mudou

    def test_patch_rejects_negative_amount(self):
        response = self.client.patch(
            self.expense_detail_url(self.expense), {'amount': '-10.00'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ExpenseDeleteTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.expense = make_expense(self.vehicle)

    def test_delete_without_deletion_reason_is_rejected(self):
        response = self.client.delete(
            self.expense_detail_url(self.expense), {}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('deletion_reason', response.data)

        self.expense.refresh_from_db()
        self.assertIsNone(self.expense.deleted_at)

    def test_delete_with_deletion_reason_soft_deletes(self):
        response = self.client.delete(
            self.expense_detail_url(self.expense),
            {'deletion_reason': 'Lançada em duplicidade'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.expense.refresh_from_db()
        self.assertIsNotNone(self.expense.deleted_at)
        self.assertEqual(self.expense.deletion_reason, 'Lançada em duplicidade')

        # soft delete, não hard delete
        self.assertTrue(VehicleExpense.all_objects.filter(pk=self.expense.pk).exists())

        # some da listagem do veículo
        list_response = self.client.get(self.expense_list_url(self.vehicle))
        ids = [row['id'] for row in list_response.data]
        self.assertNotIn(str(self.expense.pk), ids)

    def test_delete_never_hard_deletes(self):
        expense_pk = self.expense.pk
        self.client.delete(
            self.expense_detail_url(self.expense), {'deletion_reason': 'teste'}, format='json'
        )
        self.assertTrue(VehicleExpense.all_objects.filter(pk=expense_pk).exists())


class ExpenseAffectsVehicleTotalCostEndToEndTests(AuthenticatedAPITestCase):
    """Fecha o ciclo ponta a ponta via API, não direto no service: cria
    despesa -> confere total_cost no detalhe do veículo -> soft-deleta a
    despesa -> confere que total_cost caiu de volta, tudo via requisições
    HTTP reais, não chamando VehicleMetricsService diretamente."""

    def setUp(self):
        super().setUp()
        self.vehicle = make_vehicle(self.company, purchase_price=Decimal('50000.00'))

    def test_soft_deleting_expense_removes_it_from_vehicle_total_cost_via_api(self):
        baseline = self.client.get(self.vehicle_detail_url(self.vehicle))
        self.assertEqual(baseline.data['metrics']['total_cost'], '50000.00')

        create_response = self.client.post(
            self.expense_list_url(self.vehicle),
            {
                'date': '2026-01-15',
                'category': ExpenseCategory.MECHANICAL,
                'description': 'Revisão',
                'amount': '1500.00',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)
        expense_id = create_response.data['id']

        with_expense = self.client.get(self.vehicle_detail_url(self.vehicle))
        self.assertEqual(with_expense.data['metrics']['total_cost'], '51500.00')

        delete_response = self.client.delete(
            reverse('expense-detail', kwargs={'expense_id': expense_id}),
            {'deletion_reason': 'Lançamento incorreto'},
            format='json',
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        after_delete = self.client.get(self.vehicle_detail_url(self.vehicle))
        self.assertEqual(after_delete.data['metrics']['total_cost'], '50000.00')
