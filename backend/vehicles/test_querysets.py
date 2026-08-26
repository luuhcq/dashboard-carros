from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.test import TestCase
from django.utils import timezone

from core.models import Company
from vehicles.models import ExpenseCategory, Vehicle, VehicleExpense, VehicleStatus
from vehicles.querysets import annotate_vehicle_metrics
from vehicles.services import VehicleMetricsService


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


def round4(value):
    return None if value is None else value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


class AnnotationsMatchServiceTests(TestCase):
    """Confirma, veículo por veículo, que os valores calculados em SQL
    (annotate_vehicle_metrics) batem com VehicleMetricsService (Python) —
    não só que a query roda sem erro."""

    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.today = date(2026, 3, 1)

    def _assert_matches_service(self, vehicle):
        annotated = annotate_vehicle_metrics(
            Vehicle.objects.filter(pk=vehicle.pk), today=self.today
        ).get()
        metrics = VehicleMetricsService.calculate(vehicle, today=self.today)

        expected_margin = metrics.margin if vehicle.status == VehicleStatus.SOLD else metrics.projected_margin
        expected_roi = metrics.roi if vehicle.status == VehicleStatus.SOLD else metrics.projected_roi

        self.assertEqual(annotated.total_cost, metrics.total_cost, f'{vehicle}: total_cost diverge')
        self.assertEqual(annotated.aging, metrics.days_in_stock, f'{vehicle}: aging diverge')
        self.assertEqual(
            round4(annotated.margin), round4(expected_margin), f'{vehicle}: margin diverge'
        )
        self.assertEqual(round4(annotated.roi), round4(expected_roi), f'{vehicle}: roi diverge')

    def test_freshly_purchased_no_asking_price(self):
        vehicle = make_vehicle(self.company, purchase_date=date(2026, 1, 1))
        self._assert_matches_service(vehicle)

    def test_listed_with_asking_price(self):
        vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('45000.00'),
            asking_price=Decimal('55000.00'),
            purchase_date=date(2026, 1, 1),
        )
        self._assert_matches_service(vehicle)

    def test_sold_with_sale_price(self):
        vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('45000.00'),
            asking_price=Decimal('55000.00'),
            status=VehicleStatus.SOLD,
            sale_date=date(2026, 2, 10),
            sale_price=Decimal('51000.00'),
            purchase_date=date(2026, 1, 5),
        )
        self._assert_matches_service(vehicle)

    def test_asking_price_zero_no_db_error_matches_service_none(self):
        vehicle = make_vehicle(self.company, asking_price=Decimal('0'))
        self._assert_matches_service(vehicle)

    def test_purchase_price_zero_total_cost_zero_roi_none(self):
        vehicle = make_vehicle(
            self.company, purchase_price=Decimal('0'), asking_price=Decimal('100.00')
        )
        self._assert_matches_service(vehicle)

    def test_sold_without_sale_price_edge_case_does_not_fallback_to_projected(self):
        """Caso de borda: status=SOLD mas sale_price=None. Isso agora é
        bloqueado por Vehicle.clean()/full_clean() em qualquer save() normal
        (inclusive Admin) — usa .update() pra contornar e simular o estado
        mesmo assim, porque a annotation precisa continuar defensiva caso
        esse estado exista por qualquer outro caminho (migração antiga, bug
        futuro etc.). O service dá margin/roi=None (não cai pra projected)
        — a annotation replica exatamente isso, não usa asking_price aqui."""
        vehicle = make_vehicle(self.company, asking_price=Decimal('9000.00'))
        Vehicle.objects.filter(pk=vehicle.pk).update(status=VehicleStatus.SOLD)
        vehicle.refresh_from_db()

        self._assert_matches_service(vehicle)

    def test_total_expenses_excludes_soft_deleted(self):
        vehicle = make_vehicle(self.company, purchase_price=Decimal('40000.00'))
        VehicleExpense.objects.create(
            vehicle=vehicle, date=date(2026, 1, 10), category=ExpenseCategory.PARTS,
            description='ativa', amount=Decimal('500.00'),
        )
        deleted = VehicleExpense.objects.create(
            vehicle=vehicle, date=date(2026, 1, 11), category=ExpenseCategory.PARTS,
            description='deletada', amount=Decimal('9999.00'),
        )
        deleted.deleted_at = timezone.now()
        deleted.save()

        annotated = annotate_vehicle_metrics(
            Vehicle.objects.filter(pk=vehicle.pk), today=self.today
        ).get()

        self.assertEqual(annotated.total_expenses, Decimal('500.00'))
        self.assertEqual(annotated.total_cost, Decimal('40500.00'))
        self._assert_matches_service(vehicle)

    def test_aging_bucket_boundary_via_annotation(self):
        vehicle = make_vehicle(self.company, purchase_date=date(2026, 1, 1))
        annotated = annotate_vehicle_metrics(
            Vehicle.objects.filter(pk=vehicle.pk), today=date(2026, 1, 1) + timedelta(days=45)
        ).get()
        self.assertEqual(annotated.aging, 45)
