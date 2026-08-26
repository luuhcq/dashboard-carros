"""Prompt 23 — auditoria de formato de erro: todo 400/404 da API precisa
sair como JSON previsível ({"field": ["msg"]} ou {"detail": "msg"}), nunca
como página HTML de debug — um cliente que faz response.json() genérico
quebraria com um parse error, não um erro de negócio tratável.

Achado real (não teórico): as rotas aninhadas explícitas em vehicles/urls.py
(vehicles/<id>/expenses/, expenses/<id>/, vehicles/<id>/photos/, photos/<id>/)
usavam o converter <uuid:...> do Django, que só casa a URL se o segmento já
for sintaticamente um UUID — um id malformado nem chegava a resolver pra
view nenhuma, caindo direto no 404 HTML padrão do Django. As rotas do router
(vehicles/{pk}/, /price/, /sale/, /value-changes/) nunca tiveram esse
problema porque o router usa um regex permissivo por padrão. Corrigido
trocando <uuid:...> por <str:...> nessas 4 rotas E trocando o
get_object_or_404 usado em get_vehicle() (vehicles/views.py) de
django.shortcuts pro equivalente de rest_framework.generics, que também
converte ValueError/ValidationError de um id malformado em Http404 (sem
isso, o id malformado chegaria na view mas ainda estouraria 500).
"""

import uuid
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Company
from vehicles.models import Vehicle


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


class MalformedIdReturnsJsonNotHtmlTests(APITestCase):
    """Cobre as 4 rotas aninhadas explícitas que tinham o problema. As rotas
    do router (vehicles/{pk}/, /price/, /sale/, /value-changes/) já nunca
    tiveram esse bug — não precisam de teste aqui, só as explícitas."""

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
        self.company = Company.objects.create(name='Empresa erro 400')
        self.vehicle = make_vehicle(self.company)

    def _assert_clean_json_404(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('detail', response.json())  # não lança JSONDecodeError

    def test_expense_list_with_malformed_vehicle_id_returns_json_404(self):
        url = reverse('vehicle-expense-list', kwargs={'vehicle_id': 'not-a-uuid'})
        self._assert_clean_json_404(url)

    def test_photo_list_with_malformed_vehicle_id_returns_json_404(self):
        url = reverse('vehicle-photo-list', kwargs={'vehicle_id': 'not-a-uuid'})
        self._assert_clean_json_404(url)

    def test_expense_detail_with_malformed_id_returns_json_404(self):
        url = reverse('expense-detail', kwargs={'expense_id': 'not-a-uuid'})
        self._assert_clean_json_404(url)

    def test_photo_detail_with_malformed_id_returns_json_404(self):
        url = reverse('photo-detail', kwargs={'photo_id': 'not-a-uuid'})
        self._assert_clean_json_404(url)

    def test_expense_list_with_valid_but_nonexistent_vehicle_id_still_404s_cleanly(self):
        """Sanidade: o caso já funcionava (Http404 vindo de DoesNotExist),
        a correção não pode ter quebrado esse caminho."""
        url = reverse('vehicle-expense-list', kwargs={'vehicle_id': uuid.uuid4()})
        self._assert_clean_json_404(url)

    def test_expense_list_with_real_vehicle_still_works(self):
        """Sanidade: <str:...> continua aceitando um UUID de verdade
        normalmente — a correção não restringiu o caminho feliz."""
        url = reverse('vehicle-expense-list', kwargs={'vehicle_id': self.vehicle.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
