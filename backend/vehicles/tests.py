import threading
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from core.models import Company
from vehicles.models import Vehicle


def make_vehicle(company, **overrides):
    defaults = {
        'company': company,
        'brand': 'Marca',
        'model': 'Modelo',
        'purchase_date': date(2026, 1, 10),
        'purchase_price': Decimal('50000.00'),
    }
    defaults.update(overrides)
    return Vehicle.objects.create(**defaults)


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


class VehicleInternalCodeGenerationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_internal_code_is_generated_on_creation(self):
        vehicle = make_vehicle(self.company)
        self.assertRegex(vehicle.internal_code, r'^CAR-\d{6}$')

    def test_internal_codes_are_unique_and_sequential_across_multiple_creations(self):
        vehicles = [make_vehicle(self.company) for _ in range(5)]
        codes = [v.internal_code for v in vehicles]

        # únicos
        self.assertEqual(len(codes), len(set(codes)))

        # sequenciais: números consecutivos, na ordem de criação
        numbers = [int(code.split('-')[1]) for code in codes]
        self.assertEqual(numbers, list(range(numbers[0], numbers[0] + 5)))

    def test_internal_code_is_not_regenerated_on_update(self):
        vehicle = make_vehicle(self.company)
        original_code = vehicle.internal_code

        vehicle.color = 'Prata'
        vehicle.save()

        self.assertEqual(vehicle.internal_code, original_code)


class VehicleInternalCodeImmutabilityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(self.company)

    def test_changing_internal_code_on_existing_vehicle_is_rejected(self):
        original_code = self.vehicle.internal_code
        self.vehicle.internal_code = 'CAR-999999'

        with self.assertRaises(ValidationError):
            self.vehicle.save()

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.internal_code, original_code)

    def test_internal_code_preserved_across_separate_db_fetch_and_update(self):
        original_code = self.vehicle.internal_code

        fetched = Vehicle.objects.get(pk=self.vehicle.pk)
        self.assertIsNot(fetched, self.vehicle)

        fetched.notes = 'observação adicionada depois'
        fetched.save()

        fetched.refresh_from_db()
        self.assertEqual(fetched.internal_code, original_code)


class VehicleInternalCodeConcurrencyTests(TransactionTestCase):
    """Usa TransactionTestCase (em vez de TestCase) de propósito: TestCase
    envolve cada teste numa transação que só a própria thread principal
    enxerga, então threads adicionais com suas próprias conexões não veriam
    os dados. TransactionTestCase faz commits reais, permitindo concorrência
    de verdade entre conexões distintas — o mesmo cenário de duas requisições
    simultâneas batendo no Postgres.

    A garantia de unicidade em si não vem deste teste: vem do nextval() do
    Postgres, que é atômico no nível do banco (MVCC/lock interno da própria
    sequence) independentemente de qualquer coordenação em Python. Este teste
    apenas comprova esse comportamento sob concorrência real.
    """

    def test_concurrent_creation_produces_no_duplicate_internal_codes(self):
        company = Company.objects.create(name='Empresa concorrência')

        thread_count = 20
        results = []
        errors = []
        lock = threading.Lock()

        def create_vehicle():
            try:
                vehicle = make_vehicle(company)
                with lock:
                    results.append(vehicle.internal_code)
            except Exception as exc:  # pragma: no cover - só para diagnóstico de falha
                with lock:
                    errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=create_vehicle) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), thread_count)
        self.assertEqual(len(set(results)), thread_count)
