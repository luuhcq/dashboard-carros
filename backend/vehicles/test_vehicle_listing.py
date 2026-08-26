from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

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

    def list_url(self, **params):
        url = reverse('vehicle-list')
        if params:
            return f'{url}?{urlencode(params)}'
        return url


class FilterTests(AuthenticatedAPITestCase):
    def test_filter_combines_status_and_brand(self):
        matching = make_vehicle(
            self.company, brand='Honda', model='Civic', status=VehicleStatus.LISTED,
            asking_price=Decimal('60000.00'),
        )
        make_vehicle(self.company, brand='Honda', model='Fit', status=VehicleStatus.PURCHASED)
        make_vehicle(
            self.company, brand='Toyota', model='Corolla', status=VehicleStatus.LISTED,
            asking_price=Decimal('65000.00'),
        )

        response = self.client.get(self.list_url(status='LISTED', brand='Honda'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertEqual(ids, [str(matching.pk)])

    def test_filter_brand_and_model_are_case_insensitive_partial(self):
        make_vehicle(self.company, brand='Honda', model='Civic')
        response = self.client.get(self.list_url(brand='hon', model='civ'))
        self.assertEqual(len(response.data), 1)

    def test_filter_is_sold_true(self):
        sold = make_vehicle(
            self.company, status=VehicleStatus.SOLD,
            sale_date=date(2026, 2, 1), sale_price=Decimal('55000.00'),
        )
        make_vehicle(self.company, status=VehicleStatus.LISTED, asking_price=Decimal('60000.00'))

        response = self.client.get(self.list_url(is_sold='true'))

        ids = [row['id'] for row in response.data]
        self.assertEqual(ids, [str(sold.pk)])

    def test_filter_is_sold_false_excludes_sold(self):
        make_vehicle(
            self.company, status=VehicleStatus.SOLD,
            sale_date=date(2026, 2, 1), sale_price=Decimal('55000.00'),
        )
        not_sold = make_vehicle(self.company, status=VehicleStatus.LISTED, asking_price=Decimal('1'))

        response = self.client.get(self.list_url(is_sold='false'))

        ids = [row['id'] for row in response.data]
        self.assertEqual(ids, [str(not_sold.pk)])

    def test_filter_aging_bucket(self):
        # today (data do sistema) é usada como referência; escolhe purchase_date
        # bem no passado (bucket 90+) vs bem recente (bucket 0-15) pra não
        # depender de qual dia é "hoje" no momento do teste.
        old = make_vehicle(self.company, purchase_date=date(2020, 1, 1))
        recent = make_vehicle(self.company, purchase_date=date.today())

        response = self.client.get(self.list_url(aging_bucket='90+'))
        ids = [row['id'] for row in response.data]
        self.assertIn(str(old.pk), ids)
        self.assertNotIn(str(recent.pk), ids)

        response2 = self.client.get(self.list_url(aging_bucket='0-15'))
        ids2 = [row['id'] for row in response2.data]
        self.assertIn(str(recent.pk), ids2)
        self.assertNotIn(str(old.pk), ids2)


class SearchTests(AuthenticatedAPITestCase):
    def test_search_matches_internal_code_brand_model_version_plate(self):
        target = make_vehicle(
            self.company, brand='Honda', model='Civic', version='Touring', plate='ABC1D23'
        )
        make_vehicle(self.company, brand='Toyota', model='Corolla')

        for term in [target.internal_code, 'Honda', 'Civic', 'Touring', 'ABC1D23']:
            response = self.client.get(self.list_url(search=term))
            ids = [row['id'] for row in response.data]
            self.assertIn(str(target.pk), ids, f'busca por "{term}" não achou o veículo esperado')

    def test_search_excludes_non_matching(self):
        make_vehicle(self.company, brand='Honda', model='Civic')
        response = self.client.get(self.list_url(search='Ferrari'))
        self.assertEqual(len(response.data), 0)


class OrderingTests(AuthenticatedAPITestCase):
    """Cada teste usa valores bem distintos entre si — confirma a ORDEM
    real dos resultados, não só ausência de erro."""

    def setUp(self):
        super().setUp()
        self.low = make_vehicle(
            self.company, brand='A-brand', model='A-model',
            purchase_date=date(2026, 1, 1), purchase_price=Decimal('10000.00'),
            asking_price=Decimal('11000.00'),
        )
        self.mid = make_vehicle(
            self.company, brand='M-brand', model='M-model',
            purchase_date=date(2026, 2, 1), purchase_price=Decimal('50000.00'),
            asking_price=Decimal('65000.00'),
        )
        self.high = make_vehicle(
            self.company, brand='Z-brand', model='Z-model',
            purchase_date=date(2026, 3, 1), purchase_price=Decimal('90000.00'),
            asking_price=Decimal('180000.00'),
        )

    def _ids(self, response):
        return [row['id'] for row in response.data]

    def test_ordering_by_purchase_date(self):
        response = self.client.get(self.list_url(ordering='purchase_date'))
        self.assertEqual(
            self._ids(response), [str(self.low.pk), str(self.mid.pk), str(self.high.pk)]
        )

    def test_ordering_by_purchase_price_desc(self):
        response = self.client.get(self.list_url(ordering='-purchase_price'))
        self.assertEqual(
            self._ids(response), [str(self.high.pk), str(self.mid.pk), str(self.low.pk)]
        )

    def test_ordering_by_total_cost(self):
        # total_cost = purchase_price aqui (sem despesas) — mesma ordem
        response = self.client.get(self.list_url(ordering='total_cost'))
        self.assertEqual(
            self._ids(response), [str(self.low.pk), str(self.mid.pk), str(self.high.pk)]
        )

    def test_ordering_by_asking_price(self):
        response = self.client.get(self.list_url(ordering='asking_price'))
        self.assertEqual(
            self._ids(response), [str(self.low.pk), str(self.mid.pk), str(self.high.pk)]
        )

    def test_ordering_by_model(self):
        response = self.client.get(self.list_url(ordering='model'))
        self.assertEqual(
            self._ids(response), [str(self.low.pk), str(self.mid.pk), str(self.high.pk)]
        )

    def test_ordering_by_days_in_stock(self):
        # purchase_date mais antiga = mais dias em estoque = days_in_stock maior
        response = self.client.get(self.list_url(ordering='-days_in_stock'))
        self.assertEqual(
            self._ids(response), [str(self.low.pk), str(self.mid.pk), str(self.high.pk)]
        )

    def test_ordering_by_margin(self):
        # projected_margin = (asking_price - purchase_price) / asking_price
        # low: (11000-10000)/11000 = 0.0909
        # mid: (65000-50000)/65000 = 0.2308
        # high: (180000-90000)/180000 = 0.5
        response = self.client.get(self.list_url(ordering='margin'))
        self.assertEqual(
            self._ids(response), [str(self.low.pk), str(self.mid.pk), str(self.high.pk)]
        )

    def test_ordering_by_roi(self):
        # projected_roi = (asking_price - purchase_price) / purchase_price
        # low: 1000/10000=0.10 | mid: 15000/50000=0.30 | high: 90000/90000=1.00
        response = self.client.get(self.list_url(ordering='roi'))
        self.assertEqual(
            self._ids(response), [str(self.low.pk), str(self.mid.pk), str(self.high.pk)]
        )

    def test_ordering_by_total_cost_reflects_expenses_not_just_purchase_price(self):
        """Garante que a ordenação por total_cost usa mesmo o total real
        (purchase_price + despesas), não só purchase_price coincidentemente
        na mesma ordem."""
        VehicleExpense.objects.create(
            vehicle=self.low, date=date(2026, 1, 5), category=ExpenseCategory.MECHANICAL,
            description='Grande reforma', amount=Decimal('200000.00'),
        )
        # agora self.low.total_cost (210000) > self.high.total_cost (90000)
        response = self.client.get(self.list_url(ordering='total_cost'))
        self.assertEqual(
            self._ids(response), [str(self.mid.pk), str(self.high.pk), str(self.low.pk)]
        )


class QueryCountTests(AuthenticatedAPITestCase):
    """Confirma que o número de queries na listagem NÃO escala linearmente
    com a quantidade de veículos — é isso que resolve o N+1 documentado no
    Prompt 14."""

    def _create_vehicles_with_expenses(self, count):
        vehicles = []
        for i in range(count):
            vehicle = make_vehicle(
                self.company, brand=f'Brand{i}', model=f'Model{i}',
                purchase_price=Decimal('10000.00') + i,
                asking_price=Decimal('12000.00') + i,
            )
            VehicleExpense.objects.create(
                vehicle=vehicle, date=date(2026, 1, 5), category=ExpenseCategory.MECHANICAL,
                description=f'Despesa {i}', amount=Decimal('100.00'),
            )
            vehicles.append(vehicle)
        return vehicles

    def test_query_count_does_not_scale_with_vehicle_count(self):
        self._create_vehicles_with_expenses(3)
        with CaptureQueriesContext(connection) as small_capture:
            response_small = self.client.get(self.list_url())
        self.assertEqual(response_small.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_small.data), 3)

        self._create_vehicles_with_expenses(7)  # total agora: 10
        with CaptureQueriesContext(connection) as large_capture:
            response_large = self.client.get(self.list_url())
        self.assertEqual(response_large.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_large.data), 10)

        small_count = len(small_capture.captured_queries)
        large_count = len(large_capture.captured_queries)

        self.assertEqual(
            small_count,
            large_count,
            f'número de queries escalou com a quantidade de veículos: '
            f'{small_count} (3 veículos) vs {large_count} (10 veículos)',
        )
        # sanidade adicional: não é só "igual", é pequeno (não centenas)
        self.assertLessEqual(large_count, 5, f'queries demais pra uma listagem: {large_count}')
