import uuid

from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Exclui por padrão registros com soft delete (deleted_at preenchido)."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """Base abstrata para soft delete transparente: deleted_at/deletion_reason
    + manager padrão que os exclui, com all_objects para acesso explícito."""

    deleted_at = models.DateTimeField(null=True, blank=True)
    deletion_reason = models.TextField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


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
