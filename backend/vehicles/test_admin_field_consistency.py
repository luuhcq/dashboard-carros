"""Prompt 23 — segunda rodada de "Admin sem restrição de campo": a mesma
classe de lacuna já fechada em Vehicle.clean() pro par status/sale_price/
sale_date (Prompt 19, ver test_admin_sold_consistency.py) tinha mais três
instâncias não percebidas até esta revisão:

1. deleted_at/deletion_reason (Vehicle e VehicleExpense) — Admin editava os
   dois campos independentemente, sem checagem cruzada.
2. internal_code — a checagem de imutabilidade vivia em save() (raise fora
   do ciclo de full_clean()), então o form do Admin nunca via o erro antes
   de chamar obj.save(): sobrava como 500 puro em vez de erro de validação.
3. VehiclePhoto.image — Admin permitia trocar a imagem de um registro
   existente, bypassando _process_image() (só roda na criação), deixando
   EXIF (inclusive geolocalização) e thumbnail dessincronizados do arquivo
   novo — a mesma regra que VehiclePhotoUpdateSerializer já aplica na API,
   sem espelho no Admin.
4. Vehicle.asking_price/sale_price — achado na revisão de vazamento de
   auditoria (não de consistência de campo): o Admin permitia editar os
   dois valores direto no form, sem criar o VehicleValueChangeLog
   correspondente — bypassando por completo o mecanismo de auditoria que
   VehicleViewSet.price/sale (único caminho autorizado, por comentário já
   existente no código) sempre cria.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
import io

from core.models import Company
from vehicles.models import ExpenseCategory, Vehicle, VehicleExpense, VehiclePhoto, VehicleValueChangeLog


def make_vehicle(company, **overrides):
    defaults = {
        'company': company, 'brand': 'X', 'model': 'Y',
        'purchase_date': date(2026, 1, 1), 'purchase_price': Decimal('1000.00'),
    }
    defaults.update(overrides)
    return Vehicle.objects.create(**defaults)


def make_jpeg_upload(name='photo.jpg', color=(255, 0, 0)):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), color=color).save(buffer, format='JPEG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


class DeletedAtDeletionReasonModelTests(TestCase):
    """Testa SoftDeleteModel.clean() diretamente — Vehicle e VehicleExpense
    herdam a mesma regra."""

    def setUp(self):
        self.company = Company.objects.create(name='Empresa consistency')

    def test_vehicle_deleted_at_without_reason_raises(self):
        vehicle = make_vehicle(self.company)
        vehicle.deleted_at = timezone.now()
        with self.assertRaises(ValidationError) as ctx:
            vehicle.full_clean()
        self.assertIn('deletion_reason', ctx.exception.message_dict)

    def test_vehicle_reason_without_deleted_at_raises(self):
        vehicle = make_vehicle(self.company)
        vehicle.deletion_reason = 'motivo órfão'
        with self.assertRaises(ValidationError) as ctx:
            vehicle.full_clean()
        self.assertIn('deletion_reason', ctx.exception.message_dict)

    def test_vehicle_valid_soft_delete_does_not_raise(self):
        vehicle = make_vehicle(self.company)
        vehicle.deleted_at = timezone.now()
        vehicle.deletion_reason = 'cadastro em duplicidade'
        vehicle.full_clean()  # não deve levantar

    def test_expense_deleted_at_without_reason_raises(self):
        vehicle = make_vehicle(self.company)
        expense = VehicleExpense.objects.create(
            vehicle=vehicle, date=date(2026, 1, 5), category=ExpenseCategory.PARTS,
            description='Peça', amount=Decimal('100.00'),
        )
        expense.deleted_at = timezone.now()
        with self.assertRaises(ValidationError) as ctx:
            expense.full_clean()
        self.assertIn('deletion_reason', ctx.exception.message_dict)


class AdminDeletedAtRequiresReasonTests(TestCase):
    """Reproduz o caminho que confirmou a lacuna: form de edição do Admin
    com deleted_at preenchido e deletion_reason vazio salvava (302) antes da
    correção em SoftDeleteModel.clean()."""

    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin_probe2', password='AdminPass!23', email='admin2@example.com'
        )
        self.client.force_login(self.admin_user)
        self.company = Company.objects.create(name='Empresa admin deletion')
        self.vehicle = make_vehicle(self.company)

    def test_admin_change_form_rejects_deleted_at_without_reason(self):
        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y',
            'status': 'PURCHASED',
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'internal_code': self.vehicle.internal_code,
            'deleted_at_0': '2026-03-01',
            'deleted_at_1': '10:00:00',
            '_save': 'Salvar',
        })

        self.assertEqual(response.status_code, 200)  # form re-renderizado com erro
        self.vehicle.refresh_from_db()
        self.assertIsNone(self.vehicle.deleted_at)  # não mudou


class AdminInternalCodeImmutabilityTests(TestCase):
    """Antes da correção (checagem em save(), fora de clean()), esse POST
    não era capturado pelo form do Admin e vazava como 500 puro em vez de
    erro de validação."""

    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin_probe3', password='AdminPass!23', email='admin3@example.com'
        )
        self.client.force_login(self.admin_user)
        self.company = Company.objects.create(name='Empresa admin internal_code')
        self.vehicle = make_vehicle(self.company)

    def test_admin_change_form_rejects_internal_code_change_gracefully(self):
        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        original_code = self.vehicle.internal_code

        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y',
            'status': 'PURCHASED',
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'internal_code': 'CAR-999999',
            '_save': 'Salvar',
        })

        self.assertEqual(response.status_code, 200)  # form re-renderizado com erro, não 500
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.internal_code, original_code)  # não mudou

    def test_internal_code_still_editable_on_creation(self):
        """Sanidade: a correção não bloqueou o caso legítimo (internal_code
        vazio na criação, preenchido automaticamente por next_internal_code())."""
        vehicle = Vehicle(
            company=self.company, brand='Novo', model='Z',
            purchase_date=date(2026, 1, 1), purchase_price=Decimal('500.00'),
        )
        vehicle.full_clean()  # não deve levantar


class AdminVehiclePhotoImageImmutabilityTests(TestCase):
    """image só é gravável na criação — mesma regra de
    VehiclePhotoUpdateSerializer.NEVER_WRITABLE_ON_PATCH, agora espelhada no
    Admin via get_readonly_fields()."""

    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin_probe4', password='AdminPass!23', email='admin4@example.com'
        )
        self.client.force_login(self.admin_user)
        self.company = Company.objects.create(name='Empresa admin photo')
        self.vehicle = make_vehicle(self.company)
        self.photo = VehiclePhoto.objects.create(vehicle=self.vehicle, image=make_jpeg_upload())

    def test_image_field_is_readonly_on_change_form(self):
        url = f'/admin/vehicles/vehiclephoto/{self.photo.pk}/change/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="image"')

    def test_image_field_is_editable_on_add_form(self):
        url = '/admin/vehicles/vehiclephoto/add/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="image"')


class AdminCannotEditPriceFieldsWithoutAuditTrailTests(TestCase):
    """asking_price/sale_price só são graváveis via POST /price//sale/
    (que sempre criam VehicleValueChangeLog) — antes da correção, o form do
    Admin editava os dois direto, sem deixar nenhum rastro de auditoria."""

    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin_probe5', password='AdminPass!23', email='admin5@example.com'
        )
        self.client.force_login(self.admin_user)
        self.company = Company.objects.create(name='Empresa admin price')
        self.vehicle = make_vehicle(self.company, purchase_price=Decimal('1000.00'))

    def test_price_fields_still_visible_on_change_form(self):
        """Diferente de VehiclePhoto.image e de deleted_at/deletion_reason: o
        campo continua visível e editável no form — a rejeição é uma
        mensagem de erro explícita (VehicleAdminForm.clean_<field>), não um
        readonly silencioso. Ver docstring de VehicleAdminForm pra por quê
        readonly_fields foi descartado (quebra Vehicle.clean() com 500)."""
        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="asking_price"')
        self.assertContains(response, 'name="sale_price"')

    def test_posting_asking_price_via_admin_is_rejected_with_explicit_error(self):
        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y',
            'status': 'PURCHASED',
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'internal_code': self.vehicle.internal_code,
            'asking_price': '50000.00',
            '_save': 'Salvar',
        })

        self.assertEqual(response.status_code, 200)  # form re-renderizado com erro, não 500
        self.vehicle.refresh_from_db()
        self.assertIsNone(self.vehicle.asking_price)  # não mudou
        self.assertEqual(VehicleValueChangeLog.objects.filter(vehicle=self.vehicle).count(), 0)

    def test_saving_unchanged_price_fields_still_works(self):
        """Sanidade: a correção não bloqueia o form quando asking_price/
        sale_price simplesmente não mudaram (POST reenvia o valor atual)."""
        self.vehicle.asking_price = Decimal('45000.00')
        self.vehicle.save()

        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y',
            'status': 'PURCHASED',
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'internal_code': self.vehicle.internal_code,
            'asking_price': '45000.00',  # mesmo valor já salvo
            '_save': 'Salvar',
        })

        self.assertEqual(response.status_code, 302)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.asking_price, Decimal('45000.00'))
