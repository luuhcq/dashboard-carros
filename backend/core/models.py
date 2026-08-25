import uuid

from django.db import models


class Company(models.Model):
    """Empresa/revenda. Modelo mínimo hoje — preparado para multiempresa futura,
    sem lógica de troca de contexto ou permissões por empresa ainda."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.name
