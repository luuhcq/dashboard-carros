from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Company
from vehicles.models import Vehicle, VehicleStatus, VehicleValueChangeLog


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

    def price_url(self, vehicle=None):
        return reverse('vehicle-price', kwargs={'pk': (vehicle or self.vehicle).pk})

    def sale_url(self, vehicle=None):
        return reverse('vehicle-sale', kwargs={'pk': (vehicle or self.vehicle).pk})

    def value_changes_url(self, vehicle=None):
        return reverse('vehicle-value-changes', kwargs={'pk': (vehicle or self.vehicle).pk})

    def detail_url(self, vehicle=None):
        return reverse('vehicle-detail', kwargs={'pk': (vehicle or self.vehicle).pk})


class UnauthenticatedAccessTests(APITestCase):
    def setUp(self):
        company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(company)

    def test_price_requires_authentication(self):
        url = reverse('vehicle-price', kwargs={'pk': self.vehicle.pk})
        response = self.client.post(url, {'new_price': '1000', 'reason': 'x'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sale_requires_authentication(self):
        url = reverse('vehicle-sale', kwargs={'pk': self.vehicle.pk})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_value_changes_requires_authentication(self):
        url = reverse('vehicle-value-changes', kwargs={'pk': self.vehicle.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class VehiclePriceEndpointTests(AuthenticatedAPITestCase):
    def test_first_price_definition_has_none_old_value(self):
        self.assertIsNone(self.vehicle.asking_price)

        response = self.client.post(
            self.price_url(),
            {'new_price': '60000.00', 'reason': 'Preço inicial de anúncio'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.asking_price, Decimal('60000.00'))

        log = VehicleValueChangeLog.objects.get(vehicle=self.vehicle, field_name='asking_price')
        self.assertIsNone(log.old_value)
        self.assertEqual(log.new_value, Decimal('60000.00'))
        self.assertEqual(log.reason, 'Preço inicial de anúncio')

    def test_second_price_change_has_previous_value_as_old(self):
        self.client.post(
            self.price_url(), {'new_price': '60000.00', 'reason': 'Preço inicial'}, format='json'
        )

        response = self.client.post(
            self.price_url(),
            {'new_price': '58000.00', 'reason': 'Ajuste por baixa procura'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.asking_price, Decimal('58000.00'))

        self.assertEqual(
            VehicleValueChangeLog.objects.filter(
                vehicle=self.vehicle, field_name='asking_price'
            ).count(),
            2,
        )
        latest_log = VehicleValueChangeLog.objects.filter(
            vehicle=self.vehicle, field_name='asking_price'
        ).order_by('-changed_at').first()
        self.assertEqual(latest_log.old_value, Decimal('60000.00'))
        self.assertEqual(latest_log.new_value, Decimal('58000.00'))

    def test_price_without_reason_returns_400_nothing_changed(self):
        response = self.client.post(
            self.price_url(), {'new_price': '60000.00'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reason', response.data)

        self.vehicle.refresh_from_db()
        self.assertIsNone(self.vehicle.asking_price)
        self.assertEqual(
            VehicleValueChangeLog.objects.filter(vehicle=self.vehicle).count(), 0
        )

    def test_price_without_new_price_returns_400_nothing_changed(self):
        response = self.client.post(self.price_url(), {'reason': 'x'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_price', response.data)
        self.assertEqual(
            VehicleValueChangeLog.objects.filter(vehicle=self.vehicle).count(), 0
        )


class VehicleSaleEndpointTests(AuthenticatedAPITestCase):
    def test_valid_sale_transitions_status_and_creates_log(self):
        response = self.client.post(
            self.sale_url(),
            {
                'sale_price': '55000.00',
                'sale_date': '2026-02-01',
                'reason': 'Venda concluída via loja',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.SOLD)
        self.assertEqual(self.vehicle.sale_price, Decimal('55000.00'))
        self.assertEqual(self.vehicle.sale_date, date(2026, 2, 1))

        log = VehicleValueChangeLog.objects.get(vehicle=self.vehicle, field_name='sale_price')
        self.assertIsNone(log.old_value)
        self.assertEqual(log.new_value, Decimal('55000.00'))
        self.assertEqual(log.reason, 'Venda concluída via loja')

    def test_sale_date_before_purchase_date_returns_400(self):
        response = self.client.post(
            self.sale_url(),
            {
                'sale_price': '55000.00',
                'sale_date': '2025-12-31',  # antes de purchase_date=2026-01-01
                'reason': 'x',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sale_date', response.data)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.PURCHASED)
        self.assertIsNone(self.vehicle.sale_price)
        self.assertEqual(
            VehicleValueChangeLog.objects.filter(vehicle=self.vehicle).count(), 0
        )

    def test_sale_rejects_zero_sale_price(self):
        response = self.client.post(
            self.sale_url(),
            {'sale_price': '0', 'sale_date': '2026-02-01', 'reason': 'x'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sale_price', response.data)

    def test_sale_correction_on_already_sold_vehicle(self):
        first = self.client.post(
            self.sale_url(),
            {'sale_price': '55000.00', 'sale_date': '2026-02-01', 'reason': 'Venda inicial'},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)

        first_log = VehicleValueChangeLog.objects.get(
            vehicle=self.vehicle, field_name='sale_price'
        )
        first_log_pk = first_log.pk
        first_log_reason = first_log.reason
        first_log_changed_at = first_log.changed_at

        # correção: mesmo endpoint, veículo já SOLD
        second = self.client.post(
            self.sale_url(),
            {
                'sale_price': '53000.00',
                'sale_date': '2026-02-03',
                'reason': 'Desconto concedido após negociação',
            },
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.SOLD)
        self.assertEqual(self.vehicle.sale_price, Decimal('53000.00'))
        self.assertEqual(self.vehicle.sale_date, date(2026, 2, 3))

        logs = VehicleValueChangeLog.objects.filter(
            vehicle=self.vehicle, field_name='sale_price'
        ).order_by('changed_at')
        self.assertEqual(logs.count(), 2)

        new_log = logs.last()
        self.assertEqual(new_log.old_value, Decimal('55000.00'))  # preço de venda anterior
        self.assertEqual(new_log.new_value, Decimal('53000.00'))
        self.assertEqual(new_log.reason, 'Desconto concedido após negociação')

        # o log anterior continua intacto no banco — não foi editado nem removido
        first_log.refresh_from_db()
        self.assertEqual(first_log.pk, first_log_pk)
        self.assertEqual(first_log.reason, first_log_reason)
        self.assertEqual(first_log.changed_at, first_log_changed_at)
        self.assertEqual(first_log.new_value, Decimal('55000.00'))


class VehicleValueChangesListTests(AuthenticatedAPITestCase):
    def test_returns_logs_ordered_most_recent_first_covering_both_field_names(self):
        self.client.post(
            self.price_url(), {'new_price': '60000.00', 'reason': 'Preço 1'}, format='json'
        )
        self.client.post(
            self.price_url(), {'new_price': '58000.00', 'reason': 'Preço 2'}, format='json'
        )
        self.client.post(
            self.sale_url(),
            {'sale_price': '55000.00', 'sale_date': '2026-02-01', 'reason': 'Venda'},
            format='json',
        )

        response = self.client.get(self.value_changes_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        field_names = {row['field_name'] for row in response.data}
        self.assertEqual(field_names, {'asking_price', 'sale_price'})

        changed_at_values = [row['changed_at'] for row in response.data]
        self.assertEqual(changed_at_values, sorted(changed_at_values, reverse=True))

        # o mais recente é a venda (última ação feita)
        self.assertEqual(response.data[0]['field_name'], 'sale_price')
        self.assertEqual(response.data[0]['reason'], 'Venda')


class WriteSerializerStillBlocksAfterTheseEndpointsExistTests(AuthenticatedAPITestCase):
    """Confirma que este prompt não afrouxou o bloqueio do Prompt 15 — os
    endpoints dedicados são a ÚNICA porta de entrada; POST/PATCH direto em
    /api/vehicles/ continua rejeitando os dois campos."""

    def test_create_still_rejects_asking_price(self):
        response = self.client.post(
            reverse('vehicle-list'),
            {
                'company': str(self.company.id),
                'brand': 'Toyota',
                'model': 'Corolla',
                'purchase_date': '2026-01-10',
                'purchase_price': '80000.00',
                'asking_price': '95000.00',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('asking_price', response.data)

    def test_patch_still_rejects_asking_price(self):
        response = self.client.patch(
            self.detail_url(), {'asking_price': '70000.00'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('asking_price', response.data)

    def test_patch_still_rejects_sale_price(self):
        response = self.client.patch(
            self.detail_url(), {'sale_price': '55000.00'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sale_price', response.data)

    def test_patch_status_sold_directly_is_rejected(self):
        """Não fazer: status SOLD só pode acontecer via POST /sale/. Achei
        essa lacuna real ao escrever este teste — VehicleWriteSerializer não
        bloqueava status=SOLD antes desta correção; PATCH {"status": "SOLD"}
        teria produzido um veículo "vendido" sem sale_price e sem log."""
        response = self.client.patch(
            self.detail_url(), {'status': VehicleStatus.SOLD}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.PURCHASED)
        self.assertIsNone(self.vehicle.sale_price)
        self.assertEqual(
            VehicleValueChangeLog.objects.filter(
                vehicle=self.vehicle, field_name='sale_price'
            ).count(),
            0,
        )

    def test_patch_status_to_non_sold_value_still_works(self):
        """Confirma que a correção não bloqueou status em geral — só o
        valor SOLD especificamente."""
        response = self.client.patch(
            self.detail_url(), {'status': VehicleStatus.IN_PREPARATION}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.IN_PREPARATION)

    def test_create_with_status_sold_directly_is_rejected(self):
        response = self.client.post(
            reverse('vehicle-list'),
            {
                'company': str(self.company.id),
                'brand': 'Toyota',
                'model': 'Corolla',
                'purchase_date': '2026-01-10',
                'purchase_price': '80000.00',
                'status': VehicleStatus.SOLD,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_patch_status_away_from_sold_is_rejected(self):
        """Achei essa lacuna também ao ser questionado sobre ela: um veículo
        já SOLD podia ser movido pra qualquer outro status via PATCH solto
        (ex. {"status": "LISTED"}), sem tocar em sale_price/sale_date —
        deixando o veículo com status "não vendido" mas ainda carregando
        dados de venda íntegros, sem log nenhum sobre a reversão."""
        self.client.post(
            self.sale_url(),
            {'sale_price': '55000.00', 'sale_date': '2026-02-01', 'reason': 'Venda'},
            format='json',
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.SOLD)

        response = self.client.patch(
            self.detail_url(), {'status': VehicleStatus.LISTED}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.SOLD)  # não mudou
        self.assertEqual(self.vehicle.sale_price, Decimal('55000.00'))  # não mudou
