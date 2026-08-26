from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Company
from vehicles.models import ExpenseCategory, Vehicle, VehicleExpense, VehicleStatus


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


class UnauthenticatedAccessTests(APITestCase):
    def test_summary_requires_authentication(self):
        response = self.client.get(reverse('dashboard-summary'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_aging_requires_authentication(self):
        response = self.client.get(reverse('dashboard-aging'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_status_requires_authentication(self):
        response = self.client.get(reverse('dashboard-status'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class EmptyStockContractTests(AuthenticatedAPITestCase):
    """Banco sem veículo nenhum — confirma que nada lança exceção e que os
    valores voltam tratados (não None cru vazando sem decisão)."""

    def test_summary_with_no_vehicles_at_all(self):
        response = self.client.get(reverse('dashboard-summary'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'vehicles_in_stock': 0,
            'capital_employed': '0.00',
            'total_asking_price': '0.00',
            'potential_profit': '0.00',
            'average_aging_days': None,
        })

    def test_summary_with_only_sold_vehicles(self):
        """Estoque vazio não significa "banco vazio" — um veículo SOLD não
        conta como estoque, então isso também precisa cair no caso vazio."""
        make_vehicle(
            self.company, status=VehicleStatus.SOLD,
            sale_date=date(2026, 2, 1), sale_price=Decimal('55000.00'),
        )

        response = self.client.get(reverse('dashboard-summary'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vehicles_in_stock'], 0)
        self.assertEqual(response.data['capital_employed'], '0.00')
        self.assertEqual(response.data['total_asking_price'], '0.00')
        self.assertEqual(response.data['potential_profit'], '0.00')
        self.assertIsNone(response.data['average_aging_days'])

    def test_aging_with_no_vehicles_all_buckets_zero(self):
        response = self.client.get(reverse('dashboard-aging'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            '0-15': 0, '16-30': 0, '31-45': 0, '46-60': 0, '61-90': 0, '90+': 0,
        })

    def test_status_with_no_vehicles_all_statuses_zero(self):
        response = self.client.get(reverse('dashboard-status'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'PURCHASED': 0, 'IN_PREPARATION': 0, 'READY': 0,
            'LISTED': 0, 'RESERVED': 0, 'SOLD': 0,
        })


class SummaryContractAndValuesTests(AuthenticatedAPITestCase):
    """Cenário com múltiplos veículos em estados variados, valores
    conferidos manualmente."""

    def setUp(self):
        super().setUp()
        today = date.today()

        # em estoque, com asking_price, sem despesas
        self.v1 = make_vehicle(
            self.company, purchase_price=Decimal('10000.00'), asking_price=Decimal('12000.00'),
            purchase_date=today,
        )
        # em estoque, com asking_price e despesas
        self.v2 = make_vehicle(
            self.company, purchase_price=Decimal('20000.00'), asking_price=Decimal('25000.00'),
            purchase_date=today - timedelta(days=20),
        )
        VehicleExpense.objects.create(
            vehicle=self.v2, date=date(2026, 1, 5), category=ExpenseCategory.MECHANICAL,
            description='x', amount=Decimal('500.00'),
        )
        # em estoque, sem asking_price
        self.v3 = make_vehicle(
            self.company, purchase_price=Decimal('5000.00'), purchase_date=today,
        )
        # vendido — não deve contar em nada aqui
        self.v4 = make_vehicle(
            self.company, purchase_price=Decimal('7000.00'), asking_price=Decimal('9000.00'),
            status=VehicleStatus.SOLD, sale_date=date(2026, 2, 1), sale_price=Decimal('8500.00'),
            purchase_date=today,
        )

    def test_summary_contract_and_values(self):
        response = self.client.get(reverse('dashboard-summary'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()),
            {
                'vehicles_in_stock', 'capital_employed', 'total_asking_price',
                'potential_profit', 'average_aging_days',
            },
        )

        # total_cost: v1=10000.00, v2=20500.00 (com despesa), v3=5000.00 -> soma=35500.00
        self.assertEqual(response.data['vehicles_in_stock'], 3)
        self.assertEqual(response.data['capital_employed'], '35500.00')

        # total_asking_price: v1=12000 + v2=25000 (v3 não tem) = 37000.00
        self.assertEqual(response.data['total_asking_price'], '37000.00')

        # potential_profit: (12000-10000) + (25000-20500) = 2000+4500 = 6500.00
        self.assertEqual(response.data['potential_profit'], '6500.00')

        # average_aging: v1=0 dias, v2=20 dias, v3=0 dias -> media = 20/3 = 6.666... -> 6.7
        self.assertEqual(response.data['average_aging_days'], round(20 / 3, 1))

    def test_all_monetary_fields_are_strings(self):
        response = self.client.get(reverse('dashboard-summary'))
        for field in ('capital_employed', 'total_asking_price', 'potential_profit'):
            self.assertIsInstance(response.data[field], str)


class AgingDistributionTests(AuthenticatedAPITestCase):
    def test_aging_contract_and_values(self):
        today = date.today()
        make_vehicle(self.company, purchase_date=today)  # 0 dias -> 0-15
        make_vehicle(self.company, purchase_date=today - timedelta(days=20))  # 16-30
        make_vehicle(self.company, purchase_date=today - timedelta(days=100))  # 90+
        # vendido não deve contar em bucket nenhum
        make_vehicle(
            self.company, purchase_date=today - timedelta(days=200),
            status=VehicleStatus.SOLD, sale_date=date(2026, 1, 1), sale_price=Decimal('1000.00'),
        )

        response = self.client.get(reverse('dashboard-aging'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()), {'0-15', '16-30', '31-45', '46-60', '61-90', '90+'}
        )
        self.assertEqual(response.data['0-15'], 1)
        self.assertEqual(response.data['16-30'], 1)
        self.assertEqual(response.data['31-45'], 0)
        self.assertEqual(response.data['90+'], 1)
        self.assertEqual(sum(response.data.values()), 3)  # SOLD não conta


class StatusDistributionTests(AuthenticatedAPITestCase):
    def test_status_contract_and_values(self):
        make_vehicle(self.company, status=VehicleStatus.PURCHASED)
        make_vehicle(self.company, status=VehicleStatus.PURCHASED)
        make_vehicle(self.company, status=VehicleStatus.LISTED, asking_price=Decimal('1'))
        make_vehicle(
            self.company, status=VehicleStatus.SOLD,
            sale_date=date(2026, 1, 1), sale_price=Decimal('1000.00'),
        )

        response = self.client.get(reverse('dashboard-status'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()),
            {'PURCHASED', 'IN_PREPARATION', 'READY', 'LISTED', 'RESERVED', 'SOLD'},
        )
        self.assertEqual(response.data['PURCHASED'], 2)
        self.assertEqual(response.data['LISTED'], 1)
        self.assertEqual(response.data['SOLD'], 1)  # conta, diferente de summary/aging
        self.assertEqual(response.data['IN_PREPARATION'], 0)
        self.assertEqual(sum(response.data.values()), 4)


class QueryCountTests(AuthenticatedAPITestCase):
    """Confirma que os 3 endpoints não escalam com a quantidade de
    veículos. O alvo não é literalmente "1 query": toda requisição
    autenticada nesta API já gasta 1 query fixa em
    CookieJWTAuthentication.get_user() (busca o usuário do cookie JWT),
    fora do controle da view — confirmado inspecionando o SQL capturado
    antes de escrever esta asserção. Então o alvo real é 2 (1 de auth + 1
    do aggregate da view), constante independente da quantidade de
    veículos — o que importa é IGUAL entre 3 e 10 veículos, não o número
    absoluto."""

    def _create_vehicles(self, count):
        for i in range(count):
            vehicle = make_vehicle(
                self.company, brand=f'Brand{i}', asking_price=Decimal('1000.00') + i,
            )
            VehicleExpense.objects.create(
                vehicle=vehicle, date=date(2026, 1, 5), category=ExpenseCategory.MECHANICAL,
                description=f'Despesa {i}', amount=Decimal('50.00'),
            )

    def _query_count_for(self, url_name, small_n, large_n):
        self._create_vehicles(small_n)
        with CaptureQueriesContext(connection) as small_capture:
            self.client.get(reverse(url_name))

        self._create_vehicles(large_n - small_n)
        with CaptureQueriesContext(connection) as large_capture:
            self.client.get(reverse(url_name))

        return len(small_capture.captured_queries), len(large_capture.captured_queries)

    def test_summary_query_count_does_not_scale(self):
        small, large = self._query_count_for('dashboard-summary', 3, 10)
        self.assertEqual(small, large, f'{small} (3 veículos) vs {large} (10 veículos)')
        self.assertEqual(large, 2)  # 1 auth (get_user) + 1 aggregate da view

    def test_aging_query_count_does_not_scale(self):
        small, large = self._query_count_for('dashboard-aging', 3, 10)
        self.assertEqual(small, large, f'{small} (3 veículos) vs {large} (10 veículos)')
        self.assertEqual(large, 2)  # 1 auth (get_user) + 1 aggregate da view

    def test_status_query_count_does_not_scale(self):
        small, large = self._query_count_for('dashboard-status', 3, 10)
        self.assertEqual(small, large, f'{small} (3 veículos) vs {large} (10 veículos)')
        self.assertEqual(large, 2)  # 1 auth (get_user) + 1 aggregate da view
