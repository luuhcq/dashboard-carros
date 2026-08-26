import io
import os
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import connection, models, transaction
from django.utils import timezone
from PIL import Image, ImageOps

from core.models import Company, SoftDeleteModel

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


class Vehicle(SoftDeleteModel):
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Veículo'
        verbose_name_plural = 'Veículos'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_internal_code = self.internal_code

    def clean(self):
        super().clean()
        # status=SOLD sem sale_price/sale_date é um estado inconsistente que
        # já foi alcançável na prática via Django Admin (form padrão do
        # ModelAdmin não passava por essa checagem) — não é só teórico.
        # A API (VehicleWriteSerializer + POST /sale/) já impedia isso;
        # full_clean() aqui fecha o mesmo buraco pra qualquer caminho de
        # escrita, incluindo Admin e shell. Direção oposta (sale_price/
        # sale_date preenchidos com status != SOLD) também é bloqueada
        # abaixo — mesma classe de inconsistência, sentido inverso.
        if self.status == VehicleStatus.SOLD:
            errors = {}
            if self.sale_price is None:
                errors['sale_price'] = 'sale_price é obrigatório quando status é SOLD.'
            if self.sale_date is None:
                errors['sale_date'] = 'sale_date é obrigatório quando status é SOLD.'
            if errors:
                raise ValidationError(errors)
        else:
            # Mesma inconsistência, direção oposta: sale_price/sale_date
            # residual num veículo que não está (mais) SOLD — ex. alguém
            # reverte o status manualmente sem limpar os dados de venda.
            errors = {}
            if self.sale_price is not None:
                errors['sale_price'] = 'sale_price só pode estar preenchido quando status é SOLD.'
            if self.sale_date is not None:
                errors['sale_date'] = 'sale_date só pode estar preenchido quando status é SOLD.'
            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self._state.adding:
            if not self.internal_code:
                self.internal_code = next_internal_code()
        elif self._original_internal_code and self.internal_code != self._original_internal_code:
            raise ValidationError(
                {'internal_code': 'internal_code é imutável e não pode ser alterado após a criação.'}
            )

        self.full_clean()
        super().save(*args, **kwargs)
        self._original_internal_code = self.internal_code

    def __str__(self):
        return self.internal_code or str(self.id)


class ExpenseCategory(models.TextChoices):
    ACQUISITION = 'ACQUISITION', 'Aquisição'
    YARD_RELEASE = 'YARD_RELEASE', 'Pátio/Liberação'
    TRANSPORT = 'TRANSPORT', 'Transporte'
    DOCUMENTATION = 'DOCUMENTATION', 'Documentação'
    MECHANICAL = 'MECHANICAL', 'Mecânica'
    BODYWORK = 'BODYWORK', 'Funilaria'
    PAINTING = 'PAINTING', 'Pintura'
    DETAILING = 'DETAILING', 'Estética'
    CLEANING = 'CLEANING', 'Higienização'
    PARTS = 'PARTS', 'Peças'
    ACCESSORIES = 'ACCESSORIES', 'Acessórios'
    MARKETING = 'MARKETING', 'Marketing'
    COMMISSION = 'COMMISSION', 'Comissão'
    OTHER = 'OTHER', 'Outros'


class VehicleExpense(SoftDeleteModel):
    """Despesa associada a um veículo (1 Vehicle — N VehicleExpense)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='expenses')

    date = models.DateField()
    category = models.CharField(max_length=20, choices=ExpenseCategory.choices)
    description = models.CharField(max_length=255)
    supplier = models.CharField(max_length=150, null=True, blank=True)

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    paid = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Despesa do veículo'
        verbose_name_plural = 'Despesas do veículo'

    def save(self, *args, **kwargs):
        # full_clean() aqui garante que amount > 0 vale para .save()/.create()
        # direto, não só quando o chamador lembra de validar manualmente.
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_category_display()} - {self.vehicle}'


class ValueChangeField(models.TextChoices):
    ASKING_PRICE = 'asking_price', 'Preço anunciado'
    SALE_PRICE = 'sale_price', 'Preço de venda'


# Imutabilidade garantida apenas na camada de aplicação (save()/delete()
# sobrescritos), sem constraint ou trigger de banco. Decisão aceita para a V1
# dado uso single-user sem acesso SQL externo direto — revisar se o sistema
# evoluir para multiusuário ou acesso de terceiros ao banco.
class VehicleValueChangeLog(models.Model):
    """Log append-only de mudanças em asking_price/sale_price. Nunca editável
    nem excluível após criado — é o próprio mecanismo de auditoria, então
    save()/delete() bloqueiam qualquer tentativa (inclusive via Admin, que
    também está registrado como somente leitura)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name='value_change_logs'
    )

    field_name = models.CharField(max_length=20, choices=ValueChangeField.choices)
    old_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    new_value = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField()

    changed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de alteração de valor'
        verbose_name_plural = 'Logs de alteração de valor'
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.vehicle} - {self.get_field_name_display()}: {self.old_value} -> {self.new_value}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                'VehicleValueChangeLog é um log append-only; não pode ser editado após criado.'
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('VehicleValueChangeLog é um log append-only; não pode ser excluído.')


THUMBNAIL_SIZE = (400, 400)


def vehicle_photo_upload_path(instance, filename):
    return f'vehicles/{instance.vehicle_id}/photos/{filename}'


def vehicle_photo_thumbnail_upload_path(instance, filename):
    return f'vehicles/{instance.vehicle_id}/thumbnails/{filename}'


class VehiclePhoto(models.Model):
    """Foto de um veículo. No máximo uma is_cover=True por vehicle — garantido
    por UniqueConstraint parcial (rede de segurança) e, no fluxo principal,
    pela troca atômica em save().

    Sem soft delete de propósito (decisão do Prompt 18, não uma lacuna
    esquecida do Prompt 10): diferente de preço/venda, não há motivo de
    auditoria pra manter o histórico de fotos removidas — é mídia, não um
    valor financeiro sensível. DELETE remove o registro E os arquivos físicos
    (image + thumbnail) do storage — ver delete() abaixo —, pra não acumular
    lixo órfão indefinidamente no S3/filesystem local.

    Limitação conhecida: essa limpeza só roda quando delete() é chamado numa
    instância específica. Um hard delete em cascata de Vehicle (on_delete=
    CASCADE aqui) usa DELETE em lote no banco e não instancia cada
    VehiclePhoto, então não passaria por este delete() — os arquivos
    ficariam órfãos nesse cenário. Na prática isso não deveria acontecer:
    Vehicle usa soft delete como fluxo normal, hard delete de Vehicle não é
    exposto por nenhum endpoint."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='photos')

    image = models.ImageField(upload_to=vehicle_photo_upload_path)
    thumbnail = models.ImageField(
        upload_to=vehicle_photo_thumbnail_upload_path, blank=True, editable=False
    )

    position = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto do veículo'
        verbose_name_plural = 'Fotos do veículo'
        ordering = ['position', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle'],
                condition=models.Q(is_cover=True),
                name='unique_cover_photo_per_vehicle',
            ),
        ]

    def __str__(self):
        return f'Foto {self.position} - {self.vehicle}'

    def delete(self, *args, **kwargs):
        image_file = self.image
        thumbnail_file = self.thumbnail

        result = super().delete(*args, **kwargs)

        # depois do registro sumir do banco, remove os arquivos do storage
        # (save=False: não há mais linha no banco pra atualizar)
        if image_file:
            image_file.delete(save=False)
        if thumbnail_file:
            thumbnail_file.delete(save=False)

        return result

    def save(self, *args, **kwargs):
        if self._state.adding and self.image:
            self._process_image()

        if self.is_cover:
            with transaction.atomic():
                # UPDATE já toma lock de linha no Postgres; select_for_update()
                # não se aplica aqui pois .update() não passa pelo iterador do
                # queryset que respeitaria esse hint.
                VehiclePhoto.objects.filter(vehicle_id=self.vehicle_id, is_cover=True).exclude(
                    pk=self.pk
                ).update(is_cover=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def _process_image(self):
        """Remove EXIF (pode conter geolocalização) e gera thumbnail via Pillow.

        A orientação é "assada" nos pixels via exif_transpose antes do EXIF
        ser descartado, para a imagem não aparecer rotacionada depois.
        """
        self.image.open()
        self.image.seek(0)
        original = Image.open(self.image)
        original.load()
        original = ImageOps.exif_transpose(original)

        image_format = (original.format or 'JPEG').upper()
        if image_format == 'JPEG' and original.mode in ('RGBA', 'P'):
            original = original.convert('RGB')

        original_name = os.path.basename(self.image.name)

        clean_buffer = io.BytesIO()
        original.save(clean_buffer, format=image_format)
        self.image = ContentFile(clean_buffer.getvalue(), name=original_name)

        thumbnail_image = original.copy()
        thumbnail_image.thumbnail(THUMBNAIL_SIZE)
        thumb_buffer = io.BytesIO()
        thumbnail_image.save(thumb_buffer, format=image_format)
        self.thumbnail = ContentFile(thumb_buffer.getvalue(), name=f'thumb_{original_name}')
