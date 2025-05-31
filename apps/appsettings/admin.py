from django.contrib import admin
from image_cropping import ImageCroppingMixin
from import_export.admin import ImportExportModelAdmin
from apps.appsettings.models import DynamicContent
from unfold.admin import ModelAdmin


# Register your models here.
@admin.register(DynamicContent)
class DynamicContentAdmin(ImageCroppingMixin, ModelAdmin, ImportExportModelAdmin):
    readonly_fields = ('updated_at',)
    list_display = ('key', 'content_type', 'updated_at')
    list_filter = ('content_type',)
    search_fields = ('key', 'text')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('key',)
        return self.readonly_fields
