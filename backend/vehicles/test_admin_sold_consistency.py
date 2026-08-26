from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Company
from vehicles.models import Vehicle, VehicleStatus


class AdminCannotCreateInconsistentSoldStateTests(TestCase):
    """Reproduz exatamente o caminho que confirmou a lacuna: POST no form de
    edição do Django Admin com status=SOLD e sale_price/sale_date omitidos.
    Antes da correção em Vehicle.clean(), isso salvava (HTTP 302) e deixava
    o veículo em estado inconsistente. Agora precisa falhar."""

    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin_probe', password='AdminPass!23', email='admin@example.com'
        )
        self.client.force_login(self.admin_user)
        self.company = Company.objects.create(name='Empresa admin consistency')
        self.vehicle = Vehicle.objects.create(
            company=self.company, brand='X', model='Y',
            purchase_date=date(2026, 1, 1), purchase_price=Decimal('1000.00'),
        )

    def test_admin_change_form_rejects_status_sold_without_sale_price_and_date(self):
        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y',
            'status': VehicleStatus.SOLD,
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'internal_code': self.vehicle.internal_code,
            '_save': 'Salvar',
        })

        # 200 = form re-renderizado com erro (não redirecionou pra changelist)
        self.assertEqual(response.status_code, 200)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.PURCHASED)  # não mudou
        self.assertIsNone(self.vehicle.sale_price)
        self.assertIsNone(self.vehicle.sale_date)

    def test_admin_change_form_rejects_transition_to_sold_via_price_fields(self):
        """Prompt 23 tornou este caso INválido de propósito (mudança de
        comportamento, não regressão): VehicleAdminForm.clean_sale_price
        agora rejeita qualquer alteração de sale_price feita direto pelo
        Admin, então SOLD com sale_price/sale_date preenchidos manualmente
        no form deixou de ser um caminho legítimo — só POST
        /api/vehicles/{id}/sale/ pode fazer essa transição (ver
        test_admin_field_consistency.AdminCannotEditPriceFieldsWithoutAuditTrailTests)."""
        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y',
            'status': VehicleStatus.SOLD,
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'sale_date': '2026-02-01',
            'sale_price': '1200.00',
            'internal_code': self.vehicle.internal_code,
            '_save': 'Salvar',
        })

        self.assertEqual(response.status_code, 200)  # form re-renderizado com erro
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.PURCHASED)  # não mudou
        self.assertIsNone(self.vehicle.sale_price)

    def test_admin_change_form_accepts_edit_of_already_sold_vehicle_without_touching_price(self):
        """Sanidade pro caso legítimo que sobrevive à restrição acima:
        reeditar um veículo JÁ vendido (status/sale_price/sale_date
        consistentes, definidos originalmente via POST /sale/) sem alterar
        os campos de preço continua salvando normalmente."""
        self.vehicle.status = VehicleStatus.SOLD
        self.vehicle.sale_date = date(2026, 2, 1)
        self.vehicle.sale_price = Decimal('1200.00')
        self.vehicle.save()

        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y renomeado',
            'status': VehicleStatus.SOLD,
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'sale_date': '2026-02-01',
            'sale_price': '1200.00',  # reenviado sem mudar
            'internal_code': self.vehicle.internal_code,
            '_save': 'Salvar',
        })

        self.assertEqual(response.status_code, 302)  # redirecionou = salvou
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.model, 'Y renomeado')
        self.assertEqual(self.vehicle.sale_price, Decimal('1200.00'))

    def test_admin_change_form_rejects_sale_price_residual_when_not_sold(self):
        """Mesma inconsistência do teste acima, sentido oposto: status
        continua PURCHASED (não SOLD), mas sale_price é preenchido no form —
        antes da correção isso não era barrado em nenhuma direção."""
        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y',
            'status': VehicleStatus.PURCHASED,
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'sale_price': '1200.00',
            'internal_code': self.vehicle.internal_code,
            '_save': 'Salvar',
        })

        self.assertEqual(response.status_code, 200)  # form re-renderizado com erro

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.PURCHASED)
        self.assertIsNone(self.vehicle.sale_price)  # não mudou

    def test_admin_change_form_rejects_sale_date_residual_when_not_sold(self):
        """Mesma lacuna do teste acima, mas pro campo sale_date isolado (sem
        sale_price) — ramo próprio em Vehicle.clean() nunca exercitado até
        agora (achado pela cobertura no Prompt 21: o teste de sale_price
        residual não cobria esse ramo irmão)."""
        url = f'/admin/vehicles/vehicle/{self.vehicle.pk}/change/'
        response = self.client.post(url, data={
            'company': str(self.company.id),
            'brand': 'X',
            'model': 'Y',
            'status': VehicleStatus.PURCHASED,
            'purchase_date': '2026-01-01',
            'purchase_price': '1000.00',
            'sale_date': '2026-02-01',
            'internal_code': self.vehicle.internal_code,
            '_save': 'Salvar',
        })

        self.assertEqual(response.status_code, 200)  # form re-renderizado com erro

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.PURCHASED)
        self.assertIsNone(self.vehicle.sale_date)  # não mudou


class VehicleCleanDirectModelTests(TestCase):
    """Testa Vehicle.clean() diretamente (sem passar por Admin/serializer) —
    até agora essa regra só era exercitada indiretamente via Admin. Cobre os
    4 ramos: SOLD sem sale_price, SOLD sem sale_date, não-SOLD com
    sale_price residual, não-SOLD com sale_date residual."""

    def setUp(self):
        self.company = Company.objects.create(name='Empresa clean direto')

    def _vehicle(self, **overrides):
        defaults = {
            'company': self.company, 'brand': 'X', 'model': 'Y',
            'purchase_date': date(2026, 1, 1), 'purchase_price': Decimal('1000.00'),
        }
        defaults.update(overrides)
        return Vehicle(**defaults)

    def test_sold_without_sale_price_raises_on_sale_price_key(self):
        vehicle = self._vehicle(
            status=VehicleStatus.SOLD, sale_date=date(2026, 2, 1), sale_price=None
        )
        with self.assertRaises(ValidationError) as ctx:
            vehicle.full_clean()
        self.assertIn('sale_price', ctx.exception.message_dict)

    def test_sold_without_sale_date_raises_on_sale_date_key(self):
        vehicle = self._vehicle(
            status=VehicleStatus.SOLD, sale_date=None, sale_price=Decimal('1200.00')
        )
        with self.assertRaises(ValidationError) as ctx:
            vehicle.full_clean()
        self.assertIn('sale_date', ctx.exception.message_dict)

    def test_not_sold_with_sale_price_residual_raises(self):
        vehicle = self._vehicle(status=VehicleStatus.PURCHASED, sale_price=Decimal('1200.00'))
        with self.assertRaises(ValidationError) as ctx:
            vehicle.full_clean()
        self.assertIn('sale_price', ctx.exception.message_dict)

    def test_not_sold_with_sale_date_residual_raises(self):
        vehicle = self._vehicle(status=VehicleStatus.PURCHASED, sale_date=date(2026, 2, 1))
        with self.assertRaises(ValidationError) as ctx:
            vehicle.full_clean()
        self.assertIn('sale_date', ctx.exception.message_dict)

    def test_valid_sold_state_does_not_raise(self):
        vehicle = self._vehicle(
            status=VehicleStatus.SOLD, sale_date=date(2026, 2, 1), sale_price=Decimal('1200.00')
        )
        vehicle.full_clean()  # não deve levantar

    def test_valid_not_sold_state_does_not_raise(self):
        vehicle = self._vehicle(status=VehicleStatus.PURCHASED)
        vehicle.full_clean()  # não deve levantar
