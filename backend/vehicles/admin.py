from django.contrib import admin

from .models import VehicleValueChangeLog


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
