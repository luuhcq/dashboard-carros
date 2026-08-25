from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.models import Company
from vehicles.models import Vehicle


class VehicleSoftDeleteManagerTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = Vehicle.objects.create(
            company=self.company,
            purchase_date=date(2026, 1, 10),
            purchase_price=Decimal('50000.00'),
        )

    def test_alive_vehicle_appears_in_default_manager(self):
        self.assertIn(self.vehicle, Vehicle.objects.all())

    def test_soft_deleted_vehicle_does_not_appear_in_default_manager(self):
        self.vehicle.deleted_at = timezone.now()
        self.vehicle.deletion_reason = 'teste'
        self.vehicle.save()

        self.assertNotIn(self.vehicle, Vehicle.objects.all())
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_soft_deleted_vehicle_still_accessible_via_all_objects(self):
        self.vehicle.deleted_at = timezone.now()
        self.vehicle.save()

        self.assertIn(self.vehicle, Vehicle.all_objects.all())
        self.assertEqual(Vehicle.all_objects.count(), 1)
