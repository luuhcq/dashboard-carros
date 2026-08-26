import io
import tempfile
import threading
from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image

from core.models import Company
from vehicles.models import (
    ExpenseCategory,
    Vehicle,
    VehicleExpense,
    VehiclePhoto,
    VehicleValueChangeLog,
)


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


def make_uploaded_image(name='photo.jpg', size=(60, 40), color='blue', exif_bytes=None):
    buffer = io.BytesIO()
    img = Image.new('RGB', size, color=color)
    if exif_bytes is not None:
        img.save(buffer, format='JPEG', exif=exif_bytes)
    else:
        img.save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')


class VehicleSoftDeleteManagerTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = Vehicle.objects.create(
            company=self.company,
            brand='Marca',
            model='Modelo',
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


class VehicleExpenseSoftDeleteManagerTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(self.company)
        self.expense = make_expense(self.vehicle)

    def test_alive_expense_appears_in_default_manager(self):
        self.assertIn(self.expense, VehicleExpense.objects.all())

    def test_soft_deleted_expense_does_not_appear_in_default_manager(self):
        self.expense.deleted_at = timezone.now()
        self.expense.deletion_reason = 'lançado por engano'
        self.expense.save()

        self.assertNotIn(self.expense, VehicleExpense.objects.all())
        self.assertEqual(VehicleExpense.objects.count(), 0)

    def test_soft_deleted_expense_still_accessible_via_all_objects(self):
        self.expense.deleted_at = timezone.now()
        self.expense.save()

        self.assertIn(self.expense, VehicleExpense.all_objects.all())
        self.assertEqual(VehicleExpense.all_objects.count(), 1)


class VehicleExpenseAmountValidationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(self.company)

    def test_zero_amount_is_rejected(self):
        expense = VehicleExpense(
            vehicle=self.vehicle,
            date=date(2026, 1, 15),
            category=ExpenseCategory.PARTS,
            description='Peça',
            amount=Decimal('0.00'),
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()

    def test_negative_amount_is_rejected(self):
        expense = VehicleExpense(
            vehicle=self.vehicle,
            date=date(2026, 1, 15),
            category=ExpenseCategory.PARTS,
            description='Peça',
            amount=Decimal('-10.00'),
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()

    def test_positive_amount_is_accepted(self):
        expense = VehicleExpense(
            vehicle=self.vehicle,
            date=date(2026, 1, 15),
            category=ExpenseCategory.PARTS,
            description='Peça',
            amount=Decimal('10.00'),
        )
        expense.full_clean()  # não deve levantar

    def test_zero_amount_is_rejected_by_save_without_calling_full_clean_manually(self):
        """save() chama full_clean() internamente — a validação vale mesmo se
        quem chamou .save() esqueceu de validar antes, não só quando o
        chamador lembra de invocar full_clean() manualmente."""
        expense = VehicleExpense(
            vehicle=self.vehicle,
            date=date(2026, 1, 15),
            category=ExpenseCategory.PARTS,
            description='Peça',
            amount=Decimal('0.00'),
        )
        with self.assertRaises(ValidationError):
            expense.save()
        self.assertEqual(VehicleExpense.all_objects.count(), 0)

    def test_negative_amount_is_rejected_by_save_without_calling_full_clean_manually(self):
        expense = VehicleExpense(
            vehicle=self.vehicle,
            date=date(2026, 1, 15),
            category=ExpenseCategory.PARTS,
            description='Peça',
            amount=Decimal('-5.00'),
        )
        with self.assertRaises(ValidationError):
            expense.save()
        self.assertEqual(VehicleExpense.all_objects.count(), 0)

    def test_positive_amount_is_accepted_by_save_directly(self):
        expense = VehicleExpense(
            vehicle=self.vehicle,
            date=date(2026, 1, 15),
            category=ExpenseCategory.PARTS,
            description='Peça',
            amount=Decimal('10.00'),
        )
        expense.save()  # não deve levantar
        self.assertEqual(VehicleExpense.objects.count(), 1)


class VehicleValueChangeLogTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(self.company)

    def _make_log(self):
        return VehicleValueChangeLog.objects.create(
            vehicle=self.vehicle,
            field_name='asking_price',
            old_value=None,
            new_value=Decimal('60000.00'),
            reason='Primeira definição do preço anunciado',
        )

    def test_log_is_created_normally(self):
        log = self._make_log()
        self.assertEqual(VehicleValueChangeLog.objects.count(), 1)
        self.assertIsNone(log.old_value)

    def test_editing_existing_log_is_rejected(self):
        log = self._make_log()
        log.reason = 'tentando editar'

        with self.assertRaises(ValidationError):
            log.save()

    def test_deleting_log_is_rejected(self):
        log = self._make_log()

        with self.assertRaises(ValidationError):
            log.delete()

        self.assertEqual(VehicleValueChangeLog.objects.count(), 1)


class VehiclePhotoTests(TestCase):
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

    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(self.company)

    def test_constraint_prevents_two_covers_when_bypassing_application_logic(self):
        photo1 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg'), is_cover=True
        )
        photo2 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('b.jpg'), is_cover=False
        )

        # .update() vai direto pro SQL, contornando a lógica de troca atômica
        # do save() — a constraint do banco é quem tem que barrar isso.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VehiclePhoto.objects.filter(pk=photo2.pk).update(is_cover=True)

        photo1.refresh_from_db()
        self.assertTrue(photo1.is_cover)

    def test_marking_new_photo_as_cover_unsets_previous_cover(self):
        photo1 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg'), is_cover=True
        )
        photo2 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('b.jpg'), is_cover=False
        )

        photo2.is_cover = True
        photo2.save()

        photo1.refresh_from_db()
        photo2.refresh_from_db()
        self.assertFalse(photo1.is_cover)
        self.assertTrue(photo2.is_cover)

    def test_upload_generates_thumbnail_and_strips_exif(self):
        exif = Image.Exif()
        exif[0x010F] = 'Fabricante de teste'  # tag Make
        exif[0x0110] = 'Camera de teste'  # tag Model
        exif_bytes = exif.tobytes()

        uploaded = make_uploaded_image('com_exif.jpg', size=(800, 600), exif_bytes=exif_bytes)

        # confirma que a imagem de teste realmente tem EXIF antes do upload
        uploaded.seek(0)
        sanity_check = Image.open(uploaded)
        self.assertTrue(len(sanity_check.getexif()) > 0)
        uploaded.seek(0)

        photo = VehiclePhoto.objects.create(vehicle=self.vehicle, image=uploaded)

        self.assertTrue(photo.thumbnail.name)

        photo.image.open()
        persisted_image = Image.open(photo.image)
        self.assertEqual(len(persisted_image.getexif()), 0)

        photo.thumbnail.open()
        thumb_image = Image.open(photo.thumbnail)
        self.assertLessEqual(thumb_image.width, 400)
        self.assertLessEqual(thumb_image.height, 400)


class AdminSoftDeleteVisibilityTests(TestCase):
    """Confirma explicitamente que o Admin mostra registros soft-deletados de
    Vehicle e VehicleExpense (decisão consciente do PROMPT 11: o Admin troca
    para all_objects via SoftDeleteAdminMixin.get_queryset), com uma coluna
    deixando claro quais estão deletados — não é o manager `objects` (que
    exclui deletados) vazando sem ninguém ter decidido."""

    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username='admin', password='AdminPass!23', email='admin@example.com'
        )
        self.client.force_login(self.admin_user)

        self.company = Company.objects.create(name='Empresa admin')
        self.deleted_vehicle = make_vehicle(self.company, brand='Deletado', model='X')
        self.deleted_vehicle.deleted_at = timezone.now()
        self.deleted_vehicle.deletion_reason = 'teste admin'
        self.deleted_vehicle.save()

        self.active_vehicle = make_vehicle(self.company, brand='Ativo', model='Y')

        self.deleted_expense = make_expense(self.active_vehicle, description='Despesa deletada')
        self.deleted_expense.deleted_at = timezone.now()
        self.deleted_expense.save()

        self.active_expense = make_expense(self.active_vehicle, description='Despesa ativa')

    def test_vehicle_admin_changelist_shows_soft_deleted_vehicle(self):
        response = self.client.get('/admin/vehicles/vehicle/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.deleted_vehicle.internal_code)
        self.assertContains(response, self.active_vehicle.internal_code)
        # a coluna de status precisa indicar visualmente qual está deletado
        self.assertContains(response, 'Deletado')
        self.assertContains(response, 'Ativo')

    def test_vehicle_admin_queryset_uses_all_objects_not_default_manager(self):
        model_admin = admin.site._registry[Vehicle]
        request = RequestFactory().get('/admin/vehicles/vehicle/')
        request.user = self.admin_user

        qs = model_admin.get_queryset(request)

        self.assertIn(self.deleted_vehicle, qs)
        self.assertIn(self.active_vehicle, qs)
        # e confirma que isso realmente diverge do manager default (objects),
        # que é quem já exclui soft-deletados — provando que a escolha foi
        # deliberada, não um acidente de os dois coincidirem
        self.assertNotIn(self.deleted_vehicle, Vehicle.objects.all())

    def test_vehicle_expense_admin_changelist_shows_soft_deleted_expense(self):
        response = self.client.get('/admin/vehicles/vehicleexpense/')

        self.assertEqual(response.status_code, 200)
        # description não está no list_display (só vehicle/category/amount/
        # date/paid, como pedido), então a identificação da linha é pelo pk
        self.assertContains(response, str(self.deleted_expense.pk))
        self.assertContains(response, str(self.active_expense.pk))
        self.assertContains(response, 'Deletado')
        self.assertContains(response, 'Ativo')

    def test_vehicle_expense_admin_queryset_uses_all_objects_not_default_manager(self):
        model_admin = admin.site._registry[VehicleExpense]
        request = RequestFactory().get('/admin/vehicles/vehicleexpense/')
        request.user = self.admin_user

        qs = model_admin.get_queryset(request)

        self.assertIn(self.deleted_expense, qs)
        self.assertNotIn(self.deleted_expense, VehicleExpense.objects.all())


class VehiclePhotoAdminTests(TestCase):
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

    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username='admin_photo', password='AdminPass!23', email='admin2@example.com'
        )
        self.client.force_login(self.admin_user)

        self.company = Company.objects.create(name='Empresa admin foto')
        self.vehicle = make_vehicle(self.company)
        self.photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg'), is_cover=True
        )

    def test_vehicle_photo_admin_changelist_renders_thumbnail_preview(self):
        response = self.client.get('/admin/vehicles/vehiclephoto/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<img src=')
        self.assertContains(response, self.photo.thumbnail.url)
