from dataclasses import fields
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone

from core.models import Company
from vehicles.models import ExpenseCategory, Vehicle, VehicleExpense, VehicleStatus
from vehicles.services import VehicleMetrics, VehicleMetricsService


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


def make_expense(vehicle, amount, **overrides):
    defaults = {
        'vehicle': vehicle,
        'date': date(2026, 1, 5),
        'category': ExpenseCategory.MECHANICAL,
        'description': 'Despesa',
        'amount': amount,
    }
    defaults.update(overrides)
    return VehicleExpense.objects.create(**defaults)


class TotalExpensesTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_total_expenses_is_zero_when_no_expenses(self):
        vehicle = make_vehicle(self.company)
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertEqual(metrics.total_expenses, Decimal('0'))

    def test_total_expenses_sums_only_non_deleted_expenses(self):
        vehicle = make_vehicle(self.company)
        make_expense(vehicle, Decimal('100.00'))
        make_expense(vehicle, Decimal('200.00'))
        deleted = make_expense(vehicle, Decimal('9999.00'))
        deleted.deleted_at = timezone.now()
        deleted.deletion_reason = 'teste'
        deleted.save()

        metrics = VehicleMetricsService.calculate(vehicle)

        self.assertEqual(metrics.total_expenses, Decimal('300.00'))

    def test_precomputed_total_expenses_is_used_and_skips_query(self):
        vehicle = make_vehicle(self.company)
        make_expense(vehicle, Decimal('999999.00'))  # não deve ser somado

        with CaptureQueriesContext(connection) as captured:
            metrics = VehicleMetricsService.calculate(vehicle, total_expenses=Decimal('42.00'))

        self.assertEqual(metrics.total_expenses, Decimal('42.00'))
        self.assertEqual(len(captured.captured_queries), 0)

    def test_total_cost_is_purchase_price_plus_total_expenses(self):
        vehicle = make_vehicle(self.company, purchase_price=Decimal('50000.00'))
        make_expense(vehicle, Decimal('1500.50'))

        metrics = VehicleMetricsService.calculate(vehicle)

        self.assertEqual(metrics.total_cost, Decimal('51500.50'))


class FipeMetricsTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_fipe_metrics_none_when_fipe_reference_value_is_null(self):
        vehicle = make_vehicle(self.company, fipe_reference_value=None)
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertIsNone(metrics.fipe_percentage_paid)
        self.assertIsNone(metrics.fipe_discount)

    def test_fipe_metrics_none_when_fipe_reference_value_is_zero(self):
        vehicle = make_vehicle(self.company, fipe_reference_value=Decimal('0'))
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertIsNone(metrics.fipe_percentage_paid)
        self.assertIsNone(metrics.fipe_discount)

    def test_fipe_metrics_computed_correctly(self):
        vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('40000.00'),
            fipe_reference_value=Decimal('50000.00'),
        )
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertEqual(metrics.fipe_percentage_paid, Decimal('0.8'))
        self.assertEqual(metrics.fipe_discount, Decimal('0.2'))


class ProjectedMetricsTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_projected_metrics_none_when_asking_price_is_null(self):
        vehicle = make_vehicle(self.company, asking_price=None)
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertIsNone(metrics.projected_profit)
        self.assertIsNone(metrics.projected_margin)
        self.assertIsNone(metrics.projected_roi)

    def test_projected_profit_computed_when_asking_price_present(self):
        vehicle = make_vehicle(
            self.company, purchase_price=Decimal('50000.00'), asking_price=Decimal('65000.00')
        )
        make_expense(vehicle, Decimal('5000.00'))

        metrics = VehicleMetricsService.calculate(vehicle)

        # total_cost = 55000, projected_profit = 65000 - 55000 = 10000
        self.assertEqual(metrics.projected_profit, Decimal('10000.00'))
        self.assertEqual(metrics.projected_margin, Decimal('10000.00') / Decimal('65000.00'))
        self.assertEqual(metrics.projected_roi, Decimal('10000.00') / Decimal('55000.00'))

    def test_projected_profit_computed_even_when_asking_price_is_zero_but_margin_is_none(self):
        """asking_price == 0 não é None: projected_profit deve ser calculado
        (0 - total_cost). Só projected_margin, que divide por asking_price,
        vira None por causa do denominador zero — regras independentes."""
        vehicle = make_vehicle(
            self.company, purchase_price=Decimal('50000.00'), asking_price=Decimal('0')
        )

        metrics = VehicleMetricsService.calculate(vehicle)

        self.assertEqual(metrics.projected_profit, Decimal('-50000.00'))
        self.assertIsNone(metrics.projected_margin)
        # roi divide por total_cost (50000), não por asking_price — não é None
        self.assertEqual(metrics.projected_roi, Decimal('-1'))


class RealizedMetricsTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_profit_margin_roi_none_when_not_sold(self):
        vehicle = make_vehicle(self.company, status=VehicleStatus.LISTED, sale_price=None)
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertIsNone(metrics.profit)
        self.assertIsNone(metrics.margin)
        self.assertIsNone(metrics.roi)

    def test_profit_margin_roi_none_when_sold_but_sale_price_missing(self):
        """status=SOLD sem sale_price agora é bloqueado por
        Vehicle.clean()/full_clean() (ver models.py) — não dá mais pra criar
        esse estado via .save() normal. Usa .update() pra contornar o
        save()/clean() e simular o estado mesmo assim (mesmo padrão já usado
        no Prompt 10 pra testar a constraint de capa via bypass), já que o
        service precisa continuar defensivo caso esse estado exista por
        qualquer outro caminho (migração antiga, bug futuro etc.)."""
        vehicle = make_vehicle(self.company)
        Vehicle.objects.filter(pk=vehicle.pk).update(status=VehicleStatus.SOLD)
        vehicle.refresh_from_db()

        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertIsNone(metrics.profit)
        self.assertIsNone(metrics.margin)
        self.assertIsNone(metrics.roi)

    def test_profit_margin_roi_computed_when_sold(self):
        vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('50000.00'),
            status=VehicleStatus.SOLD,
            sale_date=date(2026, 2, 1),
            sale_price=Decimal('60000.00'),
        )
        make_expense(vehicle, Decimal('5000.00'))

        metrics = VehicleMetricsService.calculate(vehicle)

        # total_cost = 55000, profit = 60000 - 55000 = 5000
        self.assertEqual(metrics.profit, Decimal('5000.00'))
        self.assertEqual(metrics.margin, Decimal('5000.00') / Decimal('60000.00'))
        self.assertEqual(metrics.roi, Decimal('5000.00') / Decimal('55000.00'))


class DaysInStockAndAgingBucketTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_days_in_stock_uses_sale_date_when_sold(self):
        vehicle = make_vehicle(
            self.company,
            purchase_date=date(2026, 1, 1),
            status=VehicleStatus.SOLD,
            sale_date=date(2026, 1, 21),
            sale_price=Decimal('60000.00'),
        )
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertEqual(metrics.days_in_stock, 20)

    def test_days_in_stock_uses_today_when_not_sold(self):
        vehicle = make_vehicle(self.company, purchase_date=date(2026, 1, 1))
        metrics = VehicleMetricsService.calculate(vehicle, today=date(2026, 1, 11))
        self.assertEqual(metrics.days_in_stock, 10)

    def test_aging_bucket_boundaries(self):
        vehicle = make_vehicle(self.company, purchase_date=date(2026, 1, 1))

        cases = [
            (0, '0-15'),
            (15, '0-15'),
            (16, '16-30'),
            (30, '16-30'),
            (31, '31-45'),
            (45, '31-45'),
            (46, '46-60'),
            (60, '46-60'),
            (61, '61-90'),
            (90, '61-90'),
            (91, '90+'),
            (200, '90+'),
        ]
        for days, expected_bucket in cases:
            today = date(2026, 1, 1) + timedelta(days=days)
            metrics = VehicleMetricsService.calculate(vehicle, today=today)
            self.assertEqual(
                metrics.aging_bucket, expected_bucket, f'falhou para days={days}'
            )
            self.assertEqual(metrics.days_in_stock, days)


class ProfitPerDayTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_profit_per_day_none_when_not_sold(self):
        vehicle = make_vehicle(self.company, status=VehicleStatus.LISTED)
        metrics = VehicleMetricsService.calculate(vehicle, today=date(2026, 1, 20))
        self.assertIsNone(metrics.profit_per_day)

    def test_profit_per_day_none_when_days_in_stock_is_zero_even_with_profit(self):
        """Regra decidida explicitamente no prompt: 0 dias em estoque retorna
        None, não o próprio profit."""
        vehicle = make_vehicle(
            self.company,
            purchase_date=date(2026, 1, 1),
            purchase_price=Decimal('50000.00'),
            status=VehicleStatus.SOLD,
            sale_date=date(2026, 1, 1),  # mesmo dia -> days_in_stock == 0
            sale_price=Decimal('60000.00'),
        )
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertEqual(metrics.days_in_stock, 0)
        self.assertIsNotNone(metrics.profit)  # profit existe...
        self.assertIsNone(metrics.profit_per_day)  # ...mas profit_per_day não

    def test_profit_per_day_computed_when_sold_and_days_in_stock_positive(self):
        vehicle = make_vehicle(
            self.company,
            purchase_date=date(2026, 1, 1),
            purchase_price=Decimal('50000.00'),
            status=VehicleStatus.SOLD,
            sale_date=date(2026, 1, 11),  # 10 dias
            sale_price=Decimal('60000.00'),
        )
        metrics = VehicleMetricsService.calculate(vehicle)
        self.assertEqual(metrics.days_in_stock, 10)
        self.assertEqual(metrics.profit_per_day, metrics.profit / 10)


class NoExceptionOnEmptyDataTests(TestCase):
    """Nenhuma métrica derivada nunca deve lançar exceção não tratada, mesmo
    no cenário mais vazio possível (recém comprado, nada preenchido)."""

    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_freshly_purchased_vehicle_with_nothing_else_filled(self):
        vehicle = make_vehicle(
            self.company,
            fipe_reference_value=None,
            asking_price=None,
        )
        metrics = VehicleMetricsService.calculate(vehicle, today=date(2026, 1, 1))

        self.assertEqual(metrics.total_expenses, Decimal('0'))
        self.assertEqual(metrics.total_cost, vehicle.purchase_price)
        self.assertIsNone(metrics.fipe_percentage_paid)
        self.assertIsNone(metrics.fipe_discount)
        self.assertIsNone(metrics.projected_profit)
        self.assertIsNone(metrics.projected_margin)
        self.assertIsNone(metrics.projected_roi)
        self.assertIsNone(metrics.profit)
        self.assertIsNone(metrics.margin)
        self.assertIsNone(metrics.roi)
        self.assertIsNone(metrics.profit_per_day)
        self.assertEqual(metrics.days_in_stock, 0)
        self.assertEqual(metrics.aging_bucket, '0-15')


class DecimalPurityTests(TestCase):
    """Critério de aceite explícito: nenhum float em nenhum campo, em nenhum
    ponto — nem nos resultados intermediários que sobrevivem no retorno."""

    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def _assert_no_float_anywhere(self, metrics: VehicleMetrics):
        decimal_or_none_fields = {
            'total_expenses',
            'total_cost',
            'fipe_percentage_paid',
            'fipe_discount',
            'projected_profit',
            'projected_margin',
            'projected_roi',
            'profit',
            'margin',
            'roi',
            'profit_per_day',
        }
        for field in fields(metrics):
            value = getattr(metrics, field.name)
            self.assertNotIsInstance(
                value, float, f'{field.name} é float: {value!r}'
            )
            if field.name in decimal_or_none_fields:
                self.assertTrue(
                    value is None or isinstance(value, Decimal),
                    f'{field.name} não é Decimal nem None: {value!r} ({type(value)})',
                )

    def test_no_float_when_every_optional_field_is_populated(self):
        vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('50000.00'),
            fipe_reference_value=Decimal('55000.00'),
            asking_price=Decimal('65000.00'),
            status=VehicleStatus.SOLD,
            sale_date=date(2026, 1, 15),
            sale_price=Decimal('62000.00'),
        )
        make_expense(vehicle, Decimal('1234.56'))

        metrics = VehicleMetricsService.calculate(vehicle)

        self._assert_no_float_anywhere(metrics)
        # days_in_stock é legitimamente int (contagem de dias, não valor
        # monetário) e aging_bucket é str — os dois de propósito, fora do
        # conjunto acima.
        self.assertIsInstance(metrics.days_in_stock, int)
        self.assertIsInstance(metrics.aging_bucket, str)

    def test_no_float_when_everything_optional_is_none(self):
        vehicle = make_vehicle(self.company, fipe_reference_value=None, asking_price=None)
        metrics = VehicleMetricsService.calculate(vehicle, today=date(2026, 1, 1))
        self._assert_no_float_anywhere(metrics)


class ReferenceScenarioTests(TestCase):
    """Cenário exato do briefing do produto — valores fixos, não sintéticos,
    pra pegar qualquer regressão na fórmula que os testes genéricos (com
    números redondos) poderiam deixar passar."""

    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_reference_scenario_from_briefing(self):
        vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('37100'),
            asking_price=Decimal('45900'),
        )
        for amount in (
            Decimal('470'),
            Decimal('600'),
            Decimal('300'),
            Decimal('129'),
            Decimal('150'),
            Decimal('400'),
        ):
            make_expense(vehicle, amount)

        metrics = VehicleMetricsService.calculate(vehicle)

        self.assertEqual(metrics.total_expenses, Decimal('2049'))
        self.assertEqual(metrics.total_cost, Decimal('39149'))
        self.assertEqual(metrics.projected_profit, Decimal('6751'))

        # ≈14,71% e ≈17,25% no briefing (números arredondados pra
        # comunicação); o service não arredonda, então comparamos com
        # tolerância de 0,001 (0,1 ponto percentual) em vez de igualdade
        # exata de string.
        self.assertAlmostEqual(
            metrics.projected_margin, Decimal('0.1471'), delta=Decimal('0.001')
        )
        self.assertAlmostEqual(
            metrics.projected_roi, Decimal('0.1725'), delta=Decimal('0.001')
        )
