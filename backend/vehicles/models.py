import uuid

from django.core.exceptions import ValidationError
from django.db import connection, models

from core.models import Company

INTERNAL_CODE_SEQUENCE = 'vehicle_internal_code_seq'


def next_internal_code():
    """Consulta a sequence nativa do Postgres (nextval) e formata como CAR-XXXXXX.

    nextval() é atômico no nível do banco — duas transações concorrentes nunca
    recebem o mesmo valor, mesmo sem lock explícito na aplicação. Por isso não
    há necessidade de transaction.atomic()/select_for_update() aqui: a garantia
    de unicidade vem do próprio Postgres, não de lógica Python.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [INTERNAL_CODE_SEQUENCE])
        value = cursor.fetchone()[0]
    return f'CAR-{value:06d}'


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

    # Gerado automaticamente no save() a partir da sequence do Postgres (ver
    # next_internal_code). Imutável após a criação — ver save() abaixo.
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_internal_code = self.internal_code

    def save(self, *args, **kwargs):
        if self._state.adding:
            if not self.internal_code:
                self.internal_code = next_internal_code()
        elif self._original_internal_code and self.internal_code != self._original_internal_code:
            raise ValidationError(
                {'internal_code': 'internal_code é imutável e não pode ser alterado após a criação.'}
            )

        super().save(*args, **kwargs)
        self._original_internal_code = self.internal_code

    def __str__(self):
        return self.internal_code or str(self.id)
