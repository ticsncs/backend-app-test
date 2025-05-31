from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from apps.chat.models import PdfContent
from unfold.admin import ModelAdmin

@admin.register(PdfContent)
class PdfContentAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ('filename',)
    search_fields = ('filename',)
