from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers
from django.db import models
from django.contrib.auth.hashers import check_password

from apps.clients.models import (
    UserGroup,
    WifiPoint,
    Service,
    Referral,
    SpeedHistory,
    Transaction,
    HotspotAccount,
    UserProfile,
    Contract,
    SliderHome,
    SliderSecond,
    PaymentMethod,
    Support,
    PuntosGanados,
    SlideAction,
    TicketRating,
    RatingQuestion,
    WifiConnectionLog,
    MassPointsLoad,
    PointsCategory,
)


# ODOO URLS


class RegisterTicketSerializer(serializers.Serializer):
    numeroTicket = serializers.CharField(max_length=100, allow_blank=True)
    contrasenaAnterior = serializers.CharField(max_length=100, allow_blank=True)
    contrasenaNueva = serializers.CharField(max_length=100, allow_blank=True)
    codigoSoporte = serializers.CharField(max_length=100, allow_blank=True)
    accionLentitudServicio = serializers.CharField(max_length=100, allow_blank=True)
    redAnterior = serializers.CharField(max_length=100, allow_blank=True)
    redNueva = serializers.CharField(max_length=100, allow_blank=True)
    idDeuda = serializers.CharField(max_length=100)
    fecha = serializers.CharField(max_length=100, allow_blank=True)
    comment = serializers.CharField(max_length=255, allow_blank=True)


class ContractStatusSerializer(serializers.Serializer):
    contract = serializers.CharField(max_length=20)
    contract_id = serializers.CharField(max_length=20)


class InvoiceSerializer(serializers.Serializer):
    contract = serializers.CharField()


class TicketSearchSerializer(serializers.Serializer):
    contract = serializers.CharField()


class SupportSerializer(serializers.ModelSerializer):
    contract = serializers.CharField()


# DJANGO URLS


class WifiPointSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = WifiPoint
        fields = "__all__"


class WifiPointSerializerAll(serializers.ModelSerializer):
    class Meta:
        model = WifiPoint
        fields = ["id", "name", "latitude", "longitude", "reference", "type"]


class WifiConnectionLogSerializer(serializers.ModelSerializer):
    wifi_point = serializers.PrimaryKeyRelatedField(queryset=WifiPoint.objects.all())

    class Meta:
        model = WifiConnectionLog
        fields = ["contract_code", "wifi_point"]


class SliderSerializer(serializers.ModelSerializer):
    cropped_image_url = serializers.SerializerMethodField()

    class Meta:
        model = SliderHome
        fields = ["id", "image_field", "cropping", "title", "cropped_image_url"]

    def get_cropped_image_url(self, obj):
        request = self.context.get("request")
        cropped_url = obj.get_cropped_url()
        if cropped_url and request:
            return request.build_absolute_uri(cropped_url)
        return cropped_url


class SliderSecondSerializer(serializers.ModelSerializer):
    cropped_image_url = serializers.SerializerMethodField()

    class Meta:
        model = SliderSecond
        fields = ["id", "image_field", "cropping", "title", "cropped_image_url"]

    def get_cropped_image_url(self, obj):
        request = self.context.get("request")
        cropped_url = obj.get_cropped_url()
        if cropped_url and request:
            return request.build_absolute_uri(cropped_url)
        return cropped_url


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = "__all__"


class FatherUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "cellphone",
            "points",
        ]

class SimpleContractSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "identification",
            "telephone",
            "email",
            "contract_id",
            "productInternet",
            "user_limit",
            "son_number",
            "users",
        ]

    def get_users(self, obj):
        # Solo usuarios activos asociados al contrato
        users = UserProfile.objects.filter(contract=obj)
        return SimpleUserProfileSerializer(users, many=True, context=self.context).data

#  Ajuste para el serializador SimpleUserProfileSerializer
class SimpleUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "points",
            "image_field",
            "is_active",
            "father",
            "contract_id",  # Si es una propiedad serializada o calculada
            "date_joined"
        ]


class UserProfileSerializerLite(serializers.ModelSerializer):
    unread_notifications_count = serializers.SerializerMethodField()

    class Meta:
        fields = ("id", "is_active", "father", "points", "unread_notifications_count")
        model = UserProfile

    def get_unread_notifications_count(self, obj):
        # Count unread notifications for the current user
        return obj.notifications.filter(is_read=False).count()


class UserProfileSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        queryset=Group.objects.all(),
        required=False,
    )
    contract_id = serializers.CharField(source="contract.contract_id", read_only=True)
    contracts = serializers.SerializerMethodField()
    birth_date = serializers.DateField(
        format="%d/%m/%Y", input_formats=["%d/%m/%Y"], required=False, allow_null=True
    )

    points = serializers.IntegerField(required=False, allow_null=True, default=0)
    cropping_icon_url50x50 = serializers.SerializerMethodField()
    cropping_icon_url300x300 = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()
    privacityandterms = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = UserProfile
        exclude = ("password",)

    def get_user_permissions(self, obj):
        return obj.get_all_permissions()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["contract_id"] = (
            instance.contract.contract_id if instance.contract else None
        )
        return representation

    def get_cropping_icon_url50x50(self, obj):
        request = self.context.get("request")
        cropped_url = obj.get_cropped_url50x50()
        if cropped_url and request:
            return request.build_absolute_uri(cropped_url)
        return cropped_url

    def get_cropping_icon_url300x300(self, obj):
        request = self.context.get("request")
        cropped_url = obj.get_cropped_url300x300()
        if cropped_url and request:
            return request.build_absolute_uri(cropped_url)
        return cropped_url

    def get_contracts(self, obj):
        contracts = Contract.objects.filter(userprofile=obj)
        return ContractSerializer(contracts, many=True).data


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"


class PaymentMethodSerializer(serializers.ModelSerializer):
    cropped_image_url = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = "__all__"

    def get_cropped_image_url(self, obj):
        request = self.context.get("request")
        cropped_url = obj.get_cropped_url()
        if cropped_url and request:
            return request.build_absolute_uri(cropped_url)
        return cropped_url


class ReferralSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    referred_user_name = serializers.CharField(
        source="referred_user.username", read_only=True
    )
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = "__all__"

    def get_full_name(self, obj):
        """Retorna el nombre completo del usuario que refirió."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class SpeedHistorySerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(format="%d de %B de %Y")

    class Meta:
        model = SpeedHistory
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):
    user_points = serializers.SerializerMethodField()
    promotion_name = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    validated_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = "__all__"
        extra_kwargs = {
            "amount": {"required": False},
        }

    def get_validated_by_username(self, obj):
        return obj.validated_by.username if obj.validated_by else "-"

    def validate(self, data):
        tipo = data.get("tipo")
        codigo_promocion = data.get("codigo_promocion")
        codigo_producto = data.get("codigo_producto")
        descripcion = data.get("descripcion")
        claim_code = data.get("claim_code")

        # Validar transacciones internas
        if tipo == "Internal":
            if codigo_promocion or codigo_producto:
                raise serializers.ValidationError(
                    "Las transacciones internas no pueden tener códigos de promoción o producto."
                )
            if not descripcion:
                raise serializers.ValidationError(
                    "Las transacciones internas requieren una descripción."
                )

        # Validar transacciones de promoción
        elif tipo == "Promotion":
            if not codigo_promocion:
                raise serializers.ValidationError(
                    "Las transacciones de tipo Promoción requieren un código de promoción."
                )
            if not codigo_promocion.points_required:
                raise serializers.ValidationError(
                    "La promoción especificada no tiene puntos requeridos configurados."
                )
            data["amount"] = codigo_promocion.points_required

        # Validar transacciones de producto
        elif tipo == "Product":
            if not claim_code:
                raise serializers.ValidationError(
                    "Las transacciones de tipo Producto requieren un código de reclamo."
                )

            # Buscar la transacción que tiene este claim_code
            try:
                transaction = Transaction.objects.get(claim_code=claim_code)
            except Transaction.DoesNotExist:
                raise serializers.ValidationError("Código de reclamo no encontrado.")

            codigo_producto = transaction.codigo_producto

            if not codigo_producto:
                raise serializers.ValidationError(
                    "No se encontró un producto asociado a este reclamo."
                )

            if not codigo_producto.points_required:
                raise serializers.ValidationError(
                    "El producto especificado no tiene puntos requeridos configurados."
                )

            # Asignar automáticamente los puntos requeridos del producto
            data["amount"] = codigo_producto.points_required

        else:
            raise serializers.ValidationError("El tipo de transacción no es válido.")

        return data

    def validate_transaction_status(self, value):
        if value not in ["Pending", "Completed", "Cancelled"]:
            raise serializers.ValidationError("Estado de la transacción no válido.")
        return value

    def create(self, validated_data):
        """
        Asigna el número de puntos automáticamente antes de guardar.
        """
        tipo = validated_data.get("tipo")
        if tipo == "Promotion" and "codigo_promocion" in validated_data:
            validated_data["amount"] = validated_data[
                "codigo_promocion"
            ].points_required
        elif tipo == "Product" and "codigo_producto" in validated_data:
            validated_data["amount"] = validated_data["codigo_producto"].points_required

        return super().create(validated_data)

    def get_user_points(self, obj):
        # Devuelve los puntos actuales del usuario
        return obj.user.points

    def get_promotion_name(self, obj):
        if obj.codigo_promocion:
            return obj.codigo_promocion.title
        return None

    def get_product_name(self, obj):
        if obj.codigo_producto:
            return obj.codigo_producto.title
        return None


class HotspotAccountSerializer(serializers.ModelSerializer):
    contract_id = serializers.CharField(source="contract.contract_id", read_only=True)

    class Meta:
        model = HotspotAccount
        fields = "__all__"


class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    registration_id = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = ["username", "password", "registration_id"]

    def validate(self, attrs):
        username = attrs.get("username")  # Puede ser username, email o cédula
        password = attrs.get("password")

        # Buscar usuario por username, email o cédula
        user = UserProfile.objects.filter(
            models.Q(username=username)
            | models.Q(email=username)
            | models.Q(cedula=username)
        ).first()

        if not user:
            raise serializers.ValidationError("El usuario no está registrado")

        # Validar la contraseña manualmente sin considerar is_active
        if not check_password(password, user.password):
            raise serializers.ValidationError("Credenciales de acceso inválidas")

        # Verificar si el usuario está inactivo
        if not user.is_active:
            raise serializers.ValidationError("El usuario se encuentra deshabilitado")

        # Verificar si el usuario tiene permisos para loguearse
        if not (
            Contract.objects.filter(userprofile=user).exists()
            or user.contract_id is not None
            or user.groups.filter(name="Tiendas").exists()
            or user.is_superuser
        ):
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "Este usuario no tiene permitido iniciar sesión porque no tiene un contrato vigente."
                    ]
                }
            )

        attrs["user"] = user
        return attrs


class PuntosGanadosSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntosGanados
        fields = "__all__"


class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGroup
        fields = "__all__"


class SupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Support
        fields = "__all__"


class SlideActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlideAction
        fields = [
            "user",
            "slide_count",
        ]


class TransferPointsSerializer(serializers.Serializer):
    sender_id = serializers.IntegerField()
    receiver_id = serializers.IntegerField()
    points = serializers.IntegerField(min_value=1)
    contract_id = serializers.CharField()

    def validate(self, data):
        sender = UserProfile.objects.get(pk=data["sender_id"])
        receiver = UserProfile.objects.get(pk=data["receiver_id"])
        contract_id = data["contract_id"]

        if sender.father:
            sender_contract = Contract.objects.filter(
                userprofile=sender, contract_id=contract_id
            ).first()
            if not sender_contract:
                raise serializers.ValidationError(
                    "El usuario padre no tiene este contrato asignado."
                )
            sender_contract_id = sender_contract.contract_id
        else:
            sender_contract_id = (
                Contract.objects.filter(id=sender.contract_id)
                .values_list("contract_id", flat=True)
                .first()
            )

        if receiver.father:
            receiver_contract_id = (
                receiver.contract.contract_id if receiver.contract else contract_id
            )  # Usa contract_id enviado
        else:
            receiver_contract_id = (
                Contract.objects.filter(id=receiver.contract_id)
                .values_list("contract_id", flat=True)
                .first()
            )

        if sender == receiver:
            raise serializers.ValidationError(
                "No puedes transferirte puntos a ti mismo."
            )

        if (sender.father and receiver.father) or (
            not sender.father and not receiver.father
        ):
            raise serializers.ValidationError(
                "Las transferencias solo están permitidas entre usuario padre e hijo."
            )

        if sender.points < data["points"]:
            raise serializers.ValidationError(
                "No tienes suficientes puntos para esta transferencia."
            )

        return data


class RatingQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingQuestion
        fields = [
            "id",
            "question",
            "order",
        ]


class TicketRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketRating
        fields = ["question", "rating"]


class SupportRatingRequestSerializer(serializers.Serializer):
    ratings = TicketRatingSerializer(many=True)
    final_comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data.get("ratings"):
            raise serializers.ValidationError(
                "Debe proporcionar al menos una calificación"
            )
        return data


class TransactionRollbackSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField()

    def validate_transaction_id(self, value):
        try:
            transaction = Transaction.objects.get(id=value)
        except Transaction.DoesNotExist:
            raise serializers.ValidationError("La transacción no existe.")
        if transaction.transaction_status != "Pending":
            raise serializers.ValidationError(
                "Solo se pueden revertir transacciones pendientes."
            )
        return value

    def rollback(self):
        transaction_id = self.validated_data["transaction_id"]
        transaction = Transaction.objects.get(id=transaction_id)
        transaction.rollback()
        return transaction


class DeleteAccountSerializers(serializers.Serializer):
    id = serializers.IntegerField()


class PaymentPromiseSerializer(serializers.Serializer):
    contract = serializers.CharField(required=True)
    end_date = serializers.DateField(required=True)

    def validate_end_date(self, end_date):
        if end_date < timezone.now().date():
            raise serializers.ValidationError(
                "La fecha de finalización debe ser mayor o igual a la fecha actual."
            )
        if end_date > timezone.now().date() + timedelta(days=3):
            raise serializers.ValidationError(
                "La fecha de finalización no puede ser mayor a tres días a partir de hoy."
            )
        return end_date


class MassPointsLoadSerializer(serializers.ModelSerializer):
    # category = serializers.PrimaryKeyRelatedField(queryset=PointsCategory.objects.all())
    category = serializers.SlugRelatedField(
        queryset=PointsCategory.objects.all(), slug_field="name"
    )

    class Meta:
        model = MassPointsLoad
        fields = ["title", "category", "csv_file"]

    def create(self, validated_data):
        title = validated_data["title"]

        mass_points_load = MassPointsLoad.objects.create(
            title=title,
            category=validated_data["category"],
            csv_file=validated_data["csv_file"],
            assign_date=timezone.now(),
        )
        return mass_points_load

from rest_framework import serializers
from django.core.mail import EmailMessage

class SendMailRegisteredUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    subject = serializers.CharField()
    message = serializers.CharField()

    def send_email(self):
        email = self.validated_data['email']
        subject = self.validated_data['subject']
        message = self.validated_data['message']

        email_msg = EmailMessage(
            subject=subject,
            body=message,
            to=[email],
        )
        email_msg.send()
