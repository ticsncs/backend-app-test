from django.contrib import admin
from unfold.admin import ModelAdmin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from image_cropping import ImageCroppingMixin
from import_export.admin import ImportExportModelAdmin
from apps.store.models import Store, StoreUser, Product, Promotion, UserClaimHistory, HistoricalClaimProductHistory, \
    HistoricalClaimPromotionHistory
from simple_history.utils import update_change_reason
from django.utils.html import format_html

@admin.register(Store)
class StoreAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("name", "RUC_number", "telephone", "state")
    list_display = ("name", "email", "state", "telephone", "RUC_number", "is_enabled", "wifi_ssid")
    list_filter = ("name", "is_enabled")

    def save_model(self, request, obj, form, change):
        obj.save()
        if hasattr(obj, 'actor'):
            obj.actor = request.user
            obj.save()

    def qr_code_preview(self, obj):
        if obj.qr_wifi:
            return format_html('<img src="{}" width="100px"/>', obj.qr_wifi.url)
        return "No generado"

    qr_code_preview.allow_tags = True
    qr_code_preview.short_description = "Vista previa QR"

@admin.register(StoreUser)
class StoreUserAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("user__username", "store__name")
    list_display = ("user", "store")
    list_filter = ("store", "user")

    def save_model(self, request, obj, form, change):
        obj.save()
        if hasattr(obj, 'actor'):
            obj.actor = request.user
            obj.save()

@admin.register(UserClaimHistory)
class UserClaimHistoryAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("user__username", )
    list_display = ("user", "promotion", "product", "claims_count", "last_claim_date")
    list_filter = ("user", "promotion", "product",)

@admin.register(HistoricalClaimProductHistory)
class HistoricalClaimProductHistoryAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ("producto", "user", "status", "datetime_created", "datetime_approved", "datetime_rejected")
    list_filter = ("status", )
    search_fields = ("producto__title", "user__username", )

@admin.register(HistoricalClaimPromotionHistory)
class HistoricalClaimPromotionHistoryAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ("promocion", "user", "status", "store", "idtransaction", "datetime_created", "datetime_approved", "datetime_rejected")
    list_filter = ("status", "store" )
    search_fields = ("promocion__title", "user__username", "store__name")

@admin.register(Promotion)
class PromotionAdmin(ImageCroppingMixin, ModelAdmin, ImportExportModelAdmin):
    list_display = ("title", "store", "authorize_promotion", "is_enabled")
    list_filter = ("authorize_promotion", "is_enabled", "store")
    search_fields = ("title",)

    def get_readonly_fields(self, request, obj=None):
        """
        Restringir campos según el tipo de usuario.
        """
        if not request.user.is_superuser:
            return ["store", "authorize_promotion", "is_enabled"]
        return super().get_readonly_fields(request, obj)

    def save_model(self, request, obj, form, change):
        """
        Asigna automáticamente la tienda al crear una promoción si el usuario no es superusuario.
        """
        if not request.user.is_superuser:
            store_user = request.user.store_users.first()
            if store_user:
                obj.store = store_user.store
        super().save_model(request, obj, form, change)

        obj.save()
        if hasattr(obj, 'actor'):
            obj.actor = request.user
            obj.save()

    def get_queryset(self, request):
        """
        Filtrar promociones según el usuario.
        """
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            store_user = request.user.store_users.first()
            if store_user:
                return queryset.filter(store=store_user.store)
            return queryset.none()
        return queryset



@admin.register(Product)
class ProductAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("title",)
    list_display = ("title", "points_required", "stock", "description", "is_enabled")
    list_filter = ("status",)

    def save_model(self, request, obj, form, change):
        obj.save()
        if hasattr(obj, 'actor'):
            obj.actor = request.user
            obj.save()

# Crear el grupo "Tiendas"
# group, created = Group.objects.get_or_create(name="Tiendas")
#
# # Asignar permisos al grupo
# content_type = ContentType.objects.get_for_model(Promotion)
# permissions = Permission.objects.filter(content_type=content_type)
# group.permissions.set(permissions)