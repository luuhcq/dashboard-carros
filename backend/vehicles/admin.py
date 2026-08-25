from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Vehicle, VehicleExpense, VehiclePhoto, VehicleValueChangeLog


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


@admin.register(VehicleExpense)
class VehicleExpenseAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ('vehicle', 'category', 'amount', 'date', 'paid', 'deleted_status')
    list_filter = ('category', 'paid')
    search_fields = ('description', 'vehicle__brand', 'vehicle__model', 'vehicle__internal_code')


@admin.register(VehiclePhoto)
class VehiclePhotoAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'is_cover', 'position', 'thumbnail_preview')
    list_filter = ('is_cover',)

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
