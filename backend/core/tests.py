from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SpectacularSchemaAndDocsTests(APITestCase):
    """Só confirma que a infraestrutura de documentação está de pé (Prompt
    22) — não valida o conteúdo do schema em profundidade, isso já é
    coberto por `manage.py spectacular --fail-on-warn` rodado à parte."""

    def test_schema_endpoint_responds_200(self):
        response = self.client.get(reverse('schema'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_docs_endpoint_responds_200(self):
        response = self.client.get(reverse('swagger-ui'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
