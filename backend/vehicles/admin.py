from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Vehicle, VehicleExpense, VehiclePhoto, VehicleValueChangeLog


class VehicleAdminForm(forms.ModelForm):
    """asking_price/sale_price só são graváveis via POST /api/vehicles/{id}/
    price|sale/ (esse é o "único caminho autorizado", por comentário já
    existente em VehicleViewSet.price/sale) — sem essa checagem, o form do
    Admin editava os dois direto, mudando o preço sem criar o
    VehicleValueChangeLog correspondente: auditoria bypassada por um atalho
    não coberto por nenhum teste até esta revisão (Prompt 23).

    readonly_fields foi cogitado e descartado: torna o campo ausente do
    form, e quando Vehicle.clean() levanta ValidationError chaveado em
    'sale_price' (a checagem de consistência status=SOLD, já existente),
    o ModelForm não consegue anexar o erro a um campo que não existe mais
    nele — Django estoura ValueError (500) em vez de erro de validação.
    clean_<field> aqui roda antes de instance.full_clean() (_post_clean()),
    então intercepta a tentativa de mudança sem deixar o model chegar nesse
    caso. self.instance ainda reflete o valor original do banco neste
    ponto do ciclo (construct_instance() só roda depois, em _post_clean()),
    então dá pra comparar contra o valor submetido sem query extra.
    """

    class Meta:
        model = Vehicle
        fields = '__all__'

    def _reject_direct_price_edit(self, field_name):
        value = self.cleaned_data.get(field_name)
        if value != getattr(self.instance, field_name):
            raise forms.ValidationError(
                f'{field_name} só pode ser alterado via POST '
                f'/api/vehicles/{{id}}/{"price" if field_name == "asking_price" else "sale"}/, '
                'que registra o motivo da mudança.'
            )
        return value

    def clean_asking_price(self):
        return self._reject_direct_price_edit('asking_price')

    def clean_sale_price(self):
        return self._reject_direct_price_edit('sale_price')


class SoftDeleteAdminMixin:
    """Compartilhado por VehicleAdmin/VehicleExpenseAdmin.

    Decisão explícita: o Admin é ferramenta de contingência operacional, então
    precisa deixar ver e investigar o que foi soft-deletado — não só o que o
    manager `objects` (que já exclui deletados) mostraria por padrão. Por isso
    get_queryset troca para `all_objects` aqui, e uma coluna deixa claro quais
    registros estão deletados.
    """

    def get_queryset(self, request):
        qs = self.model.all_objects.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    @admin.display(description='Status')
    def deleted_status(self, obj):
        if obj.deleted_at:
            return mark_safe('<span style="color:#b00020;font-weight:bold;">🗑 Deletado</span>')
        return mark_safe('<span style="color:#2e7d32;">Ativo</span>')


@admin.register(Vehicle)
class VehicleAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        'internal_code',
        'brand',
        'model',
        'status',
        'purchase_date',
        'asking_price',
        'deleted_status',
    )
    list_filter = ('status', 'company')
    search_fields = ('internal_code', 'brand', 'model', 'plate')
    form = VehicleAdminForm


@admin.register(VehicleExpense)
class VehicleExpenseAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ('vehicle', 'category', 'amount', 'date', 'paid', 'deleted_status')
    list_filter = ('category', 'paid')
    search_fields = ('description', 'vehicle__brand', 'vehicle__model', 'vehicle__internal_code')


@admin.register(VehiclePhoto)
class VehiclePhotoAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'is_cover', 'position', 'thumbnail_preview')
    list_filter = ('is_cover',)

    def get_readonly_fields(self, request, obj=None):
        """image só é gravável na criação — mesma regra já aplicada na API
        via VehiclePhotoUpdateSerializer.NEVER_WRITABLE_ON_PATCH (Prompt 18):
        _process_image() (remoção de EXIF + geração de thumbnail) só roda em
        VehiclePhoto.save() quando _state.adding é True, então trocar a
        imagem de um registro existente pelo Admin (sem essa restrição)
        deixava EXIF — inclusive geolocalização — e thumbnail
        dessincronizados do arquivo novo, sem nenhum aviso (achado no
        Prompt 23)."""
        if obj is not None:
            return ('image',)
        return ()

    @admin.display(description='Preview')
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="height: 60px;" />', obj.thumbnail.url)
        return '—'


@admin.register(VehicleValueChangeLog)
class VehicleValueChangeLogAdmin(admin.ModelAdmin):
    """Somente leitura: este model é um log append-only (ver save()/delete()
    em VehicleValueChangeLog) — não deve ser editável nem excluível por
    nenhum caminho, incluindo o Admin."""

    list_display = ('vehicle', 'field_name', 'old_value', 'new_value', 'changed_at')
    list_filter = ('field_name',)
    readonly_fields = [field.name for field in VehicleValueChangeLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
