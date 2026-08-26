from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
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

    def test_admin_change_form_accepts_status_sold_with_sale_price_and_date(self):
        """Confirma que a correção não bloqueou o caso válido — sanidade."""
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

        self.assertEqual(response.status_code, 302)  # redirecionou = salvou

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatus.SOLD)
        self.assertEqual(self.vehicle.sale_price, Decimal('1200.00'))
        self.assertEqual(self.vehicle.sale_date, date(2026, 2, 1))

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
