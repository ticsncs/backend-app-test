from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.hashers import make_password
from django.core.checks import messages
from django.db import models
from image_cropping import ImageCroppingMixin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import Widget
from unfold.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django.contrib import messages
from simple_history.admin import SimpleHistoryAdmin
from django.utils.html import format_html

from apps.clients.models import (
    Contract,
    UserProfile,
    SpeedHistory,
    Referral,
    HotspotAccount,
    PhysicalAddress,
    Equipe,
    Transaction,
    WifiPoint,
    Service,
    SliderHome,
    SliderSecond,
    PaymentMethod,
    Support,
    PuntosGanados,
    SlideAction,
    RatingQuestion,
    TicketRating,
    MassPointsLoad,
    InternetPlan,
    PointsCategory,
    PointsByPlanCategory,
    WifiConnectionLog,
)

admin.site.site_title = "Nettplus"
admin.site.site_header = "NETTPLUS"
admin.site.index_title = "Administración de Nettplus"


@admin.register(InternetPlan)
class InternetPlanAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "user_limit", "speed", "wifi_accounts")
    list_filter = ("name",)


class SafeFloatWidget(Widget):
    def clean(self, value, row=None, **kwargs):
        if value in [None, "", "None"]:
            return None
        try:
            # Reemplaza comas por puntos si existen (para evitar errores con decimales en CSV)
            value = str(value).replace(",", ".")
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Valor inválido para Float: '{value}'")


class ContractResource(resources.ModelResource):
    onuId = fields.Field(
        column_name="onuId", attribute="onuId", widget=SafeFloatWidget()
    )

    class Meta:
        model = Contract
        import_id_fields = ("contract_id",)
        fields = "__all__"

    def before_import_row(self, row, **kwargs):
        if Contract.objects.filter(contract_id=row["contract_id"]).exists():
            raise ValueError(
                f"El contract_id {row['contract_id']} ya existe en la base de datos."
            )


# Register your models here.
@admin.register(Contract)
class ContractAdminClass(ModelAdmin, ImportExportModelAdmin):
    resource = ContractResource
    search_fields = ("contract_id",)
    list_display = ("contract_id", "get_son_number", "planInternet", "userprofile")
    list_filter = (
        "typeService",
        "typePlan",
    )

    @admin.display(description="Nro. Usuarios Hijos")
    def get_son_number(self, obj):
        return obj.son_number

    def save_model(self, request, obj, form, change):
        obj.save()
        if hasattr(obj, "actor"):
            obj.actor = request.user
            obj.save()


@admin.register(UserProfile)
class UserProfileAdmin(
    ImageCroppingMixin, ModelAdmin, ImportExportModelAdmin, SimpleHistoryAdmin
):
    search_fields = ("username", "email", "usercontract__contract_id")
    list_display = ("username", "email", "points", "father")
    list_filter = ("is_active", "is_staff")
    formfield_overrides = {
        models.ManyToManyField: {
            "widget": FilteredSelectMultiple("Items", is_stacked=False)
        },
    }
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (
            "Personal Info",
            {
                "fields": (
                    "first_name",
                    "cedula",
                    "birth_date",
                    "points",
                    "father",
                    "fatherstore",
                    "image_field",
                    "cropping50x50",
                    "cropping300x300",
                    "cellphone",
                    "privacityandterms",
                    "contract",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups")},
        ),
    )
    # readonly_fields = ("password",)

    def save_model(self, request, obj, form, change):
        if obj.password:
            if not obj.password.startswith("pbkdf2_sha256$"):
                obj.password = make_password(obj.password)
        obj.save()
        if hasattr(obj, "actor"):
            obj.actor = request.user
            obj.save()


@admin.register(SpeedHistory)
class SpeedHistoryAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("user__username",)
    list_display = ("user", "speed", "upload", "download", "jitter", "ping")
    list_filter = ("user",)


@admin.register(Referral)
class ReferralAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("user__username", "referred_name", "referred_email")
    list_display = ("user", "referred_name", "referred_email", "referred_phone")
    list_filter = ("user",)


@admin.register(HotspotAccount)
class HotspotAccountAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("contract__contract_id", "username_hotspot")
    list_display = ("contract", "username_hotspot", "date_create")
    list_filter = ("contract",)


@admin.register(PhysicalAddress)
class PhysicalAddressAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("contract__contract_id", "nodo")
    list_display = ("contract", "nodo", "cajaNAP", "equipoCore")
    list_filter = ("nodo",)


@admin.register(Equipe)
class EquipeAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("contract__contract_id", "nameTechnician")
    list_display = ("contract", "nameTechnician", "serialOnu", "modelRouter")
    list_filter = ("nameTechnician",)


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ["id", "descripcion", "codigo_promocion__id", "codigo_producto__id"]
    list_display = [
        "id",
        "user",
        "amount",
        "saldo",
        "tipo",
        "status",
        "transaction_status",
        "date",
    ]
    list_filter = ["transaction_status", "status", "tipo"]
    actions = ["rollback_transactions"]

    @admin.action(description="Realizar rollback de transacciones pendientes")
    def rollback_transactions(self, request, queryset):
        for transaction in queryset:
            if transaction.transaction_status == "Pending":
                try:
                    transaction.rollback()
                    messages.success(
                        request,
                        f"Rollback realizado para la transacción {transaction.id}.",
                    )
                except ValidationError as e:
                    messages.error(
                        request, f"Error en la transacción {transaction.id}: {e}"
                    )
                except Exception as e:
                    messages.error(
                        request,
                        f"Error inesperado en la transacción {transaction.id}: {e}",
                    )
            else:
                messages.warning(
                    request,
                    f"La transacción {transaction.id} no está en estado pendiente.",
                )


@admin.register(WifiPoint)
class WifiPointAdmin(ImportExportModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "type_display", "latitude", "longitude", "reference")
    list_filter = (
        "name",
        "type",
    )

    def type_display(self, obj):
        return obj.get_type_display()

    type_display.short_description = "Tipo"


@admin.register(WifiConnectionLog)
class WifiConnectionLogAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ("user", "contract_code", "wifi_point", "created_at")
    search_fields = ("user__username", "contract_code", "wifi_point__name")
    list_filter = ("wifi_point", "created_at")


@admin.register(Service)
class ServiceAdmin(ModelAdmin, ImportExportModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "description")
    list_filter = ("name",)


class TicketRatingInline(admin.TabularInline):
    model = TicketRating
    extra = 0


@admin.register(Support)
class SupportAdmin(ImageCroppingMixin, ModelAdmin, ImportExportModelAdmin):
    inlines = [TicketRatingInline]
    search_fields = ("support_id",)
    list_display = ("support_id", "comment")
    list_filter = ("support_id",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "support_id",
                    "comment",
                    "image_field",
                    "cropping50x50",
                    "final_comment",
                    "is_rated",
                )
            },
        ),
    )


@admin.register(
    RatingQuestion,
)
class RatingQuestionAdmin(ModelAdmin, ImportExportModelAdmin):
    pass


@admin.register(TicketRating)
class TicketRatingAdmin(ModelAdmin, ImportExportModelAdmin):
    pass


@admin.register(PaymentMethod)
class PaymentMethodAdmin(ImageCroppingMixin, ModelAdmin, ImportExportModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "description")
    list_filter = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "description", "image_field", "cropping50x50")}),
    )


@admin.register(PuntosGanados)
class PuntosGanadosAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ("title", "date", "points", "status", "is_enabled")
    list_filter = ("status", "is_enabled")
    search_fields = ("title",)


@admin.register(SliderHome)
class SliderHomeAdmin(ImageCroppingMixin, ModelAdmin, ImportExportModelAdmin):
    pass


@admin.register(SliderSecond)
class SliderSecondAdmin(ImageCroppingMixin, ModelAdmin, ImportExportModelAdmin):
    list_display = ("title",)


@admin.register(SlideAction)
class SlideActionAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = (
        "user",
        "slide_count",
    )
    list_filter = ("user",)
    readonly_fields = ("user", "slide_count")
    search_fields = ("user__username",)


@admin.action(description="Procesar asignación masiva de puntos")
def process_massive_assignment(modeladmin, request, queryset):
    for category in queryset:
        if category.is_massive:
            total = category.assign_massive_points()
            modeladmin.message_user(
                request,
                f"Asignados {total} usuarios en la categoría '{category.name}'.",
                messages.SUCCESS,
            )
        else:
            modeladmin.message_user(
                request,
                f"La categoría '{category.name}' no es masiva.",
                messages.WARNING,
            )


@admin.register(PointsCategory)
class PointsCategoryAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ("name", "description", "enabled")
    search_fields = ("name", "description")
    ordering = ("name",)
    list_filter = ("is_massive", "only_privacy_terms", "only_with_fathers")
    actions = [process_massive_assignment]

    def get_readonly_fields(self, request, obj=None):
        if obj and not obj.is_massive:
            return self.readonly_fields + ("massive_date",)
        return self.readonly_fields


@admin.register(PointsByPlanCategory)
class PointsByPlanCategoryAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ("category", "plan", "points")
    list_filter = ("category", "plan")
    search_fields = ("category__name", "plan__name")
    ordering = ("category", "plan")


@admin.register(MassPointsLoad)
class MassPointsLoadAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = (
        "title",
        "assign_date",
        "category",
        "is_credited",
        "download_error_csv",
    )
    list_filter = ("is_credited", "category")
    search_fields = ("title", "category__name")
    actions = ["process_points"]
    readonly_fields = ("is_credited", "download_error_csv")

    @admin.display(description="Archivo de Errores")
    def download_error_csv(self, obj):
        if obj.error_csv:
            return format_html(
                '<a href="{}" download>Descargar CSV</a>', obj.error_csv.url
            )
        return "—"

    @admin.action(description="Procesar carga masiva de puntos")
    def process_points(self, request, queryset):
        for obj in queryset:
            if not obj.is_credited:
                try:
                    obj.process_csv_and_assign_points()
                    self.message_user(
                        request,
                        f"Carga de puntos '{obj.title}' procesada exitosamente.",
                        messages.SUCCESS,
                    )
                except ValidationError as e:
                    self.message_user(
                        request, f"Error en '{obj.title}': {e}", messages.ERROR
                    )
                except Exception as e:
                    self.message_user(
                        request,
                        f"Error inesperado en '{obj.title}': {e}",
                        messages.ERROR,
                    )
            else:
                self.message_user(
                    request,
                    f"La carga '{obj.title}' ya fue procesada.",
                    messages.WARNING,
                )
