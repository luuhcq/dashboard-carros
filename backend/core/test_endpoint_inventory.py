"""Prompt 23 — checkpoint arquitetural: fixa o conjunto real de endpoints de
aplicação (16, confirmado no Prompt 22 comparando contra o schema OpenAPI e
get_resolver()) num teste, pra que uma rota adicionada/removida sem querer
quebre a suíte em vez de só divergir silenciosamente numa contagem que
ninguém vai lembrar de conferir de novo.

Usa o schema gerado pelo drf-spectacular, não get_resolver() bruto: o schema
já resolve de graça os dois problemas que uma reimplementação manual teria
que tratar do zero — variantes de format-suffix (vehicles.json etc.) e a
view raiz do DefaultRouter (api-root) nunca aparecem como paths, só
endpoints de verdade aparecem. /api/schema/ e /api/docs/ também não
aparecem (um schema não se autodocumenta) — são infraestrutura de
documentação, não endpoints de aplicação, mesma distinção já feita no
Prompt 22.

Compara o CONJUNTO de paths, não só a contagem: um endpoint removido e outro
adicionado no mesmo commit manteria a contagem em 16, mas mudaria o
conjunto — assertEqual de sets pega esse caso, len() sozinho não pegaria.
"""

from django.test import TestCase
from drf_spectacular.generators import SchemaGenerator

EXPECTED_APPLICATION_ENDPOINTS = {
    '/api/auth/login/',
    '/api/auth/logout/',
    '/api/auth/me/',
    '/api/auth/refresh/',
    '/api/dashboard/aging/',
    '/api/dashboard/status/',
    '/api/dashboard/summary/',
    '/api/expenses/{expense_id}/',
    '/api/photos/{photo_id}/',
    '/api/vehicles/',
    '/api/vehicles/{id}/',
    '/api/vehicles/{id}/price/',
    '/api/vehicles/{id}/sale/',
    '/api/vehicles/{id}/value-changes/',
    '/api/vehicles/{vehicle_id}/expenses/',
    '/api/vehicles/{vehicle_id}/photos/',
}


class ApplicationEndpointInventoryTests(TestCase):
    def test_application_endpoint_set_matches_expected_inventory(self):
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)
        actual = set(schema['paths'].keys())

        missing = EXPECTED_APPLICATION_ENDPOINTS - actual
        unexpected = actual - EXPECTED_APPLICATION_ENDPOINTS

        self.assertEqual(
            actual, EXPECTED_APPLICATION_ENDPOINTS,
            f'Inventário de endpoints mudou (esperados: {len(EXPECTED_APPLICATION_ENDPOINTS)}, '
            f'atuais: {len(actual)}). Removidos: {missing or "nenhum"}. '
            f'Novos: {unexpected or "nenhum"}. Se a mudança foi intencional, '
            'atualize EXPECTED_APPLICATION_ENDPOINTS aqui.'
        )

    def test_application_endpoint_count_is_16(self):
        """Redundante com o teste acima de propósito — a contagem sozinha é
        o número que o Prompt 22 já citou e que fica fácil de conferir de
        cabeça; o teste de set acima é quem realmente pega drift."""
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)
        self.assertEqual(len(schema['paths']), 16)
