import io
import json
import tempfile
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.renderers import JSONRenderer

from core.models import Company
from vehicles.models import (
    ExpenseCategory,
    Vehicle,
    VehicleExpense,
    VehiclePhoto,
    VehicleStatus,
    VehicleValueChangeLog,
)
from vehicles.serializers import (
    VehicleDetailSerializer,
    VehicleExpenseSerializer,
    VehicleListSerializer,
    VehiclePhotoSerializer,
    VehicleValueChangeLogSerializer,
    _round_metric_for_display,
)


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


def render_json(serializer):
    """Renderiza de fato via JSONRenderer (não só .data) — é isso que vai
    pro navegador; é isso que precisa ser confirmado, não .data isolado."""
    return json.loads(JSONRenderer().render(serializer.data))


class HondaCivicScenarioTests(TestCase):
    """Reaproveita o cenário do Prompt 12 (Honda Civic vendido) pra conferir
    o payload JSON de detalhe de ponta a ponta, com valores exatos."""

    def setUp(self):
        self.company = Company.objects.create(name='Demonstração')
        self.vehicle = make_vehicle(
            self.company,
            brand='Honda',
            model='Civic',
            purchase_date=date(2026, 1, 5),
            purchase_price=Decimal('45000.00'),
            fipe_reference_value=Decimal('52000.00'),
            asking_price=Decimal('55000.00'),
            status=VehicleStatus.SOLD,
            sale_date=date(2026, 2, 10),
            sale_price=Decimal('53000.00'),
        )
        VehicleExpense.objects.create(
            vehicle=self.vehicle, date=date(2026, 1, 6), category=ExpenseCategory.MECHANICAL,
            description='Revisão', amount=Decimal('1200.00'),
        )
        VehicleExpense.objects.create(
            vehicle=self.vehicle, date=date(2026, 1, 7), category=ExpenseCategory.PAINTING,
            description='Pintura', amount=Decimal('800.00'),
        )
        VehicleExpense.objects.create(
            vehicle=self.vehicle, date=date(2026, 1, 8), category=ExpenseCategory.DETAILING,
            description='Higienização', amount=Decimal('300.00'),
        )

    def test_detail_payload_monetary_fields_are_strings(self):
        payload = render_json(VehicleDetailSerializer(self.vehicle))

        for field in ('purchase_price', 'fipe_reference_value', 'asking_price', 'sale_price'):
            self.assertIsInstance(payload[field], str, f'{field} não é string: {payload[field]!r}')

        self.assertEqual(payload['purchase_price'], '45000.00')
        self.assertEqual(payload['fipe_reference_value'], '52000.00')
        self.assertEqual(payload['asking_price'], '55000.00')
        self.assertEqual(payload['sale_price'], '53000.00')

    def test_detail_payload_metrics_present_and_correct(self):
        payload = render_json(VehicleDetailSerializer(self.vehicle))
        metrics = payload['metrics']

        # valores conferidos manualmente no Prompt 12 pro mesmo cenário
        self.assertEqual(metrics['total_expenses'], '2300.00')
        self.assertEqual(metrics['total_cost'], '47300.00')
        self.assertEqual(metrics['projected_profit'], '7700.00')
        self.assertEqual(metrics['profit'], '5700.00')
        self.assertEqual(metrics['days_in_stock'], 36)
        self.assertEqual(metrics['aging_bucket'], '31-45')

        # frações arredondadas pra 4 casas (0.8653846153846... -> 0.8654)
        self.assertEqual(metrics['fipe_percentage_paid'], '0.8654')
        self.assertEqual(metrics['fipe_discount'], '0.1346')
        self.assertEqual(metrics['projected_margin'], '0.1400')

        expected_margin = str((Decimal('5700.00') / Decimal('53000.00')).quantize(Decimal('0.0001')))
        self.assertEqual(metrics['margin'], expected_margin)

        expected_profit_per_day = str((Decimal('5700.00') / 36).quantize(Decimal('0.01')))
        self.assertEqual(metrics['profit_per_day'], expected_profit_per_day)

    def test_all_13_metrics_keys_present_as_explicit_values(self):
        payload = render_json(VehicleDetailSerializer(self.vehicle))
        metrics = payload['metrics']

        expected_keys = {
            'total_expenses', 'total_cost', 'fipe_percentage_paid', 'fipe_discount',
            'projected_profit', 'projected_margin', 'projected_roi',
            'profit', 'margin', 'roi', 'days_in_stock', 'aging_bucket', 'profit_per_day',
        }
        self.assertEqual(set(metrics.keys()), expected_keys)
        # nenhuma métrica desse cenário é None, mas o teste de "null
        # explícito" fica no cenário separado abaixo (veículo recém comprado)

    def test_metrics_are_never_raw_float_in_rendered_json(self):
        payload = render_json(VehicleDetailSerializer(self.vehicle))
        for key, value in payload['metrics'].items():
            self.assertNotIsInstance(value, float, f'{key} veio como float: {value!r}')


class NullMetricsExplicitTests(TestCase):
    """Veículo recém comprado: metade das métricas é None. Confirma que
    aparecem como `null` explícito no JSON, não como chave ausente."""

    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(
            self.company,
            fipe_reference_value=None,
            asking_price=None,
        )

    def test_none_metrics_are_explicit_null_not_missing_keys(self):
        payload = render_json(VehicleDetailSerializer(self.vehicle))
        metrics = payload['metrics']

        for key in ('fipe_percentage_paid', 'fipe_discount', 'projected_profit',
                    'projected_margin', 'projected_roi', 'profit', 'margin',
                    'roi', 'profit_per_day'):
            self.assertIn(key, metrics, f'{key} está ausente do payload, deveria estar presente com null')
            self.assertIsNone(metrics[key])


class VehicleListSerializerTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')

    def test_list_fields_present(self):
        vehicle = make_vehicle(self.company, asking_price=Decimal('60000.00'))
        payload = render_json(VehicleListSerializer(vehicle))

        expected_keys = {
            'id', 'internal_code', 'brand', 'model', 'model_year', 'mileage',
            'status', 'purchase_date', 'fipe_reference_value', 'asking_price',
            'total_cost', 'margin', 'aging_bucket', 'days_in_stock',
        }
        self.assertEqual(set(payload.keys()), expected_keys)

    def test_list_uses_projected_margin_when_not_sold(self):
        vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('50000.00'),
            asking_price=Decimal('60000.00'),
            status=VehicleStatus.LISTED,
        )
        payload = render_json(VehicleListSerializer(vehicle))

        expected = str((Decimal('10000.00') / Decimal('60000.00')).quantize(Decimal('0.0001')))
        self.assertEqual(payload['margin'], expected)

    def test_list_uses_realized_margin_when_sold(self):
        vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('50000.00'),
            status=VehicleStatus.SOLD,
            sale_date=date(2026, 1, 15),
            sale_price=Decimal('58000.00'),
        )
        payload = render_json(VehicleListSerializer(vehicle))

        expected = str((Decimal('8000.00') / Decimal('58000.00')).quantize(Decimal('0.0001')))
        self.assertEqual(payload['margin'], expected)

    def test_list_monetary_fields_are_strings(self):
        vehicle = make_vehicle(self.company, fipe_reference_value=Decimal('55000.00'))
        payload = render_json(VehicleListSerializer(vehicle))

        self.assertIsInstance(payload['fipe_reference_value'], str)
        self.assertIsInstance(payload['total_cost'], str)


class DecimalFieldConfirmedAsStringTests(TestCase):
    """Confirma de fato (não assume) que DecimalField do DRF serializa como
    string tanto em .data quanto no JSON final renderizado."""

    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(
            self.company,
            purchase_price=Decimal('37100.00'),
        )

    def test_decimal_field_is_string_at_data_level(self):
        serializer = VehicleDetailSerializer(self.vehicle)
        self.assertIsInstance(serializer.data['purchase_price'], str)
        self.assertEqual(serializer.data['purchase_price'], '37100.00')

    def test_decimal_field_is_string_in_rendered_json_not_float(self):
        rendered_bytes = JSONRenderer().render(VehicleDetailSerializer(self.vehicle).data)
        rendered_text = rendered_bytes.decode('utf-8')

        # se tivesse virado float, apareceria 37100.0 (sem aspas) no JSON,
        # não "37100.00" (com aspas)
        self.assertIn('"purchase_price":"37100.00"', rendered_text.replace(' ', ''))
        self.assertNotIn('37100.0,', rendered_text)

        parsed = json.loads(rendered_bytes)
        self.assertIsInstance(parsed['purchase_price'], str)


class VehicleExpenseSerializerWriteTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(self.company)

    def test_deleted_at_and_deletion_reason_are_read_only(self):
        serializer = VehicleExpenseSerializer()
        self.assertIn('deleted_at', serializer.fields)
        self.assertIn('deletion_reason', serializer.fields)
        self.assertTrue(serializer.fields['deleted_at'].read_only)
        self.assertTrue(serializer.fields['deletion_reason'].read_only)

    def test_creating_expense_with_deleted_at_in_payload_is_ignored(self):
        data = {
            'vehicle': str(self.vehicle.id),
            'date': '2026-01-15',
            'category': ExpenseCategory.PARTS,
            'description': 'Peça',
            'amount': '150.00',
            'deleted_at': '2026-01-01T00:00:00Z',
            'deletion_reason': 'tentando burlar via API',
        }
        serializer = VehicleExpenseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        expense = serializer.save()

        self.assertIsNone(expense.deleted_at)
        self.assertIsNone(expense.deletion_reason)

    def test_amount_validator_from_model_is_enforced_by_serializer(self):
        data = {
            'vehicle': str(self.vehicle.id),
            'date': '2026-01-15',
            'category': ExpenseCategory.PARTS,
            'description': 'Peça',
            'amount': '-10.00',
        }
        serializer = VehicleExpenseSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_read_output_includes_deleted_at_field_for_investigation(self):
        expense = VehicleExpense.objects.create(
            vehicle=self.vehicle, date=date(2026, 1, 15), category=ExpenseCategory.PARTS,
            description='Peça', amount=Decimal('150.00'),
        )
        payload = render_json(VehicleExpenseSerializer(expense))
        self.assertIn('deleted_at', payload)
        self.assertIsNone(payload['deleted_at'])


class VehicleValueChangeLogSerializerReadOnlyTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(self.company)
        self.log = VehicleValueChangeLog.objects.create(
            vehicle=self.vehicle,
            field_name='asking_price',
            old_value=None,
            new_value=Decimal('60000.00'),
            reason='Primeira definição',
        )

    def test_read_serialization_works(self):
        payload = render_json(VehicleValueChangeLogSerializer(self.log))
        self.assertEqual(payload['new_value'], '60000.00')
        self.assertEqual(payload['reason'], 'Primeira definição')

    def test_all_fields_are_read_only(self):
        serializer = VehicleValueChangeLogSerializer()
        for field_name, field in serializer.fields.items():
            self.assertTrue(field.read_only, f'{field_name} não é read_only')

    def test_create_raises_not_implemented_even_if_is_valid_passes(self):
        data = {
            'vehicle': str(self.vehicle.id),
            'field_name': 'sale_price',
            'new_value': '99999.00',
            'reason': 'tentando escrever via API mesmo sem endpoint',
        }
        serializer = VehicleValueChangeLogSerializer(data=data)
        # is_valid passa porque não há nada a validar: todos os campos são
        # read_only, então o input é simplesmente ignorado na validação —
        # é exatamente por isso que confiar só em read_only_fields não basta.
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(NotImplementedError):
            serializer.save()

        self.assertEqual(VehicleValueChangeLog.objects.count(), 1)  # nada novo foi criado

    def test_update_raises_not_implemented(self):
        serializer = VehicleValueChangeLogSerializer(instance=self.log, data={'reason': 'tentando editar'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(NotImplementedError):
            serializer.save()

        self.log.refresh_from_db()
        self.assertEqual(self.log.reason, 'Primeira definição')  # não mudou


def make_uploaded_image(name='photo.jpg', size=(60, 40), color='blue'):
    buffer = io.BytesIO()
    Image.new('RGB', size, color=color).save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')


class VehiclePhotoSerializerTests(TestCase):
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

    def test_thumbnail_is_read_only(self):
        serializer = VehiclePhotoSerializer()
        self.assertTrue(serializer.fields['thumbnail'].read_only)

    def test_creating_photo_ignores_thumbnail_in_payload_and_generates_its_own(self):
        data = {
            'vehicle': str(self.vehicle.id),
            'image': make_uploaded_image(),
            'thumbnail': make_uploaded_image('fake_thumb.jpg'),  # deve ser ignorado
            'position': 0,
            'is_cover': True,
        }
        serializer = VehiclePhotoSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        photo = serializer.save()

        self.assertTrue(photo.thumbnail.name)
        self.assertNotIn('fake_thumb', photo.thumbnail.name)

    def test_read_output_includes_thumbnail_url(self):
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image(), is_cover=True
        )
        payload = render_json(VehiclePhotoSerializer(photo))
        self.assertIn('thumbnail', payload)
        self.assertTrue(payload['thumbnail'])


class RoundingModeTests(TestCase):
    """Prova visivelmente que o arredondamento de exibição usa ROUND_HALF_UP
    explícito, não o default do Python (ROUND_HALF_EVEN / banker's rounding)
    — com valores de borda onde os dois modos dão resultados diferentes, não
    valores genéricos onde a escolha do modo seria invisível no resultado."""

    def test_money_field_rounds_half_up_not_half_even(self):
        # 100.125 -> HALF_UP: 100.13 | HALF_EVEN (default do Python): 100.12
        result = _round_metric_for_display('total_cost', Decimal('100.125'))
        self.assertEqual(result, '100.13')
        self.assertNotEqual(result, '100.12')  # seria o resultado se fosse HALF_EVEN

    def test_fraction_field_rounds_half_up_not_half_even(self):
        # 0.12345 -> HALF_UP: 0.1235 | HALF_EVEN (default do Python): 0.1234
        result = _round_metric_for_display('margin', Decimal('0.12345'))
        self.assertEqual(result, '0.1235')
        self.assertNotEqual(result, '0.1234')  # seria o resultado se fosse HALF_EVEN

    def test_another_money_boundary_where_half_even_would_round_down_to_even(self):
        # 47300.005 -> HALF_UP: 47300.01 | HALF_EVEN: 47300.00 (0 é par)
        result = _round_metric_for_display('total_expenses', Decimal('47300.005'))
        self.assertEqual(result, '47300.01')
