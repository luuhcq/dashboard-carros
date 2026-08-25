import uuid

from django.db import models

from core.models import Company


class VehicleStatus(models.TextChoices):
    PURCHASED = 'PURCHASED', 'Comprado'
    IN_PREPARATION = 'IN_PREPARATION', 'Em preparação'
    READY = 'READY', 'Pronto'
    LISTED = 'LISTED', 'Anunciado'
    RESERVED = 'RESERVED', 'Reservado'
    SOLD = 'SOLD', 'Vendido'


class VehicleQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class VehicleManager(models.Manager):
    """Exclui por padrão registros com soft delete (deleted_at preenchido)."""

    def get_queryset(self):
        return VehicleQuerySet(self.model, using=self._db).alive()


class Vehicle(models.Model):
    """Entidade central do sistema — um veículo em estoque de uma Company.

    Regras de validação a implementar na API (serializer), não aqui:
    - sale_date >= purchase_date, quando sale_date estiver presente.
    - sale_price > 0, quando presente.
    - mileage >= 0.
    - Valores monetários (purchase_price, fipe_reference_value, asking_price,
      sale_price) >= 0.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Gerado via sequence na etapa 07; aqui só o campo. Único quando preenchido,
    # e imutável por convenção de aplicação (não há enforcement de imutabilidade
    # no banco).
    internal_code = models.CharField(max_length=50, unique=True, null=True, blank=True)

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='vehicles')

    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    version = models.CharField(max_length=100, null=True, blank=True)
    manufacture_year = models.PositiveSmallIntegerField(null=True, blank=True)
    model_year = models.PositiveSmallIntegerField(null=True, blank=True)
    mileage = models.PositiveIntegerField(null=True, blank=True)
    plate = models.CharField(max_length=10, null=True, blank=True)
    chassis = models.CharField(max_length=30, null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=VehicleStatus.choices, default=VehicleStatus.PURCHASED
    )

    source = models.CharField(max_length=100, null=True, blank=True)
    supplier_name = models.CharField(max_length=150, null=True, blank=True)

    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2)

    fipe_reference_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    fipe_code = models.CharField(max_length=20, null=True, blank=True)

    asking_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    sale_date = models.DateField(null=True, blank=True)
    sale_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True)
    deletion_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VehicleManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'Veículo'
        verbose_name_plural = 'Veículos'

    def __str__(self):
        return self.internal_code or str(self.id)
