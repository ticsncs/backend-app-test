import io
import random
import string
import uuid

from django.core.files.base import ContentFile

from apps.clients.validators.email_validator import verificar_dominio_email
from threading import local
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.timezone import now
from fcm_django.models import FCMDevice
from simple_history.models import HistoricalRecords
from auditlog.registry import auditlog
from image_cropping import ImageRatioField, ImageCropField
from image_cropping.utils import get_backend
from django.db import transaction as db_transaction
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import os
from django.conf import settings
from datetime import datetime

from apps.notifications.services import (
    UserNotificationService,
    FirebaseNotificationService,
)
from apps.store.models import (
    Promotion,
    Product,
    UserClaimHistory,
    HistoricalClaimProductHistory,
    HistoricalClaimPromotionHistory,
)


class InternetPlan(models.Model):
    name = models.CharField(
        max_length=100, unique=True, verbose_name="Nombre del Plan"
    )  # Ej: PLAN BASICO GPON
    user_limit = models.PositiveIntegerField(
        default=0, verbose_name="Límite de Usuarios Hijos"
    )
    speed = models.CharField(
        max_length=20, default=0
    )
    wifi_accounts = models.PositiveBigIntegerField(
        default=0
    )
    class Meta:
        verbose_name = "Plan de Internet"
        verbose_name_plural = "Planes de Internet"

    def generate_name_speed(self):
        name_speed = f"{self.name} {self.speed} MBPS"
        return name_speed

    def __str__(self):
        return self.generate_name_speed()
    
class Contract(models.Model):
    userprofile = models.ForeignKey(
        "UserProfile",
        on_delete=models.CASCADE,
        related_name="usercontract",
        blank=True,
        null=True,
        verbose_name="Usuario",
    )
    type_identification = models.CharField(
        blank=True, max_length=20, verbose_name="Tipo de Identificación"
    )
    identification = models.CharField(
        blank=True, max_length=15, verbose_name="Identificación"
    )
    name = models.CharField(blank=True, max_length=150, verbose_name="Nombre Cliente")
    addressComplete = models.TextField(
        null=True, blank=True, verbose_name="Dirección Completa"
    )
    email = models.EmailField(blank=True, verbose_name="Email Cliente")
    telephone = models.CharField(blank=True, max_length=50, verbose_name="Teléfono")
    cellphone = models.CharField(blank=True, max_length=50, verbose_name="Celular")
    contract_id = models.CharField(
        blank=True, max_length=20, verbose_name="Código Contrato"
    )  # Codigo

    odoo_id_contract = models.CharField(
        blank=True, max_length=20, verbose_name="Id contrato", null=True
    )
    typeService = models.CharField(
        blank=True, max_length=150, verbose_name="Tipo de Servicio"
    )
    typePlan = models.CharField(blank=True, max_length=150, verbose_name="Tipo de Plan")
    perioduse = models.CharField(
        blank=True, max_length=200, verbose_name="Periodo de Uso"
    )
    timeSpent = models.CharField(
        blank=True, max_length=100, verbose_name="Tiempo de Permanencia"
    )
    productInternet = models.CharField(
        blank=True, max_length=100, verbose_name="Producto Internet"
    )
    planInternet = models.ForeignKey(
        InternetPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Producto Internet",
    )
    typeBilling = models.CharField(
        blank=True, max_length=150, verbose_name="Tipo de Facturación"
    )
    formPayment = models.CharField(
        blank=True, max_length=150, verbose_name="Forma de Pago"
    )
    recurringBilling = models.BooleanField(
        blank=True, default=False, verbose_name="Facturación Recurrente"
    )
    dateNextBilling = models.DateField(
        null=True, blank=True, verbose_name="Fecha de Proxima Factura"
    )
    disabled = models.BooleanField(
        blank=True, default=False, verbose_name="Discapacitado"
    )
    senior = models.BooleanField(blank=True, default=False, verbose_name="Tercera Edad")
    activatePrepayment = models.BooleanField(
        blank=True, default=False, verbose_name="Activa Pago Anticipado"
    )
    addressPrincipal = models.CharField(
        blank=True, max_length=150, verbose_name="Calle Principal"
    )
    addressSecondary = models.CharField(
        blank=True, max_length=150, verbose_name="Calle Secundaria"
    )
    addressReference = models.CharField(
        blank=True, max_length=200, verbose_name="Referencia de Dirección"
    )
    geolatitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Latitud Geografia",
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    geolongitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Longitud Geografia",
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    country = models.CharField(blank=True, max_length=100, verbose_name="País")
    state = models.CharField(blank=True, max_length=100, verbose_name="Estado")
    city = models.CharField(blank=True, max_length=100, verbose_name="Ciudad")
    parish = models.CharField(blank=True, max_length=100, verbose_name="Parroquia")
    neighborhood = models.CharField(blank=True, max_length=100, verbose_name="Barrio")
    zip = models.CharField(null=True, max_length=100, blank=True, verbose_name="Zip")
    registeredArcotel = models.BooleanField(
        blank=True, default=True, verbose_name="Registro para Arcotel"
    )
    son_number = models.IntegerField(
        blank=True, null=True, verbose_name="Nro. Usuarios Hijos"
    )
    typeLink = models.CharField(
        blank=True, max_length=150, verbose_name="Tipo de Enlace"
    )
    node = models.CharField(blank=True, max_length=100, verbose_name="Nodo")
    cajaNap = models.CharField(blank=True, max_length=100, verbose_name="Caja Nap")
    equipmentCore = models.CharField(
        blank=True, max_length=100, verbose_name="Equipo Core"
    )
    equipmentOLT = models.CharField(
        blank=True, max_length=100, verbose_name="Equipo OLT"
    )
    cardOLT = models.CharField(blank=True, max_length=100, verbose_name="Tarjeta OLT")
    portOLT = models.CharField(blank=True, max_length=100, verbose_name="Puerto OLT")
    splitterSecondary = models.CharField(
        blank=True, max_length=100, verbose_name="Splitter Secundario"
    )
    serialOnu = models.CharField(blank=True, max_length=50, verbose_name="Serial Onu")
    modelOnu = models.CharField(blank=True, max_length=50, verbose_name="Model Onu")
    bridge = models.BooleanField(blank=True, default=False, verbose_name="Brigde")
    serialRouter = models.CharField(
        blank=True, max_length=75, verbose_name="Serial Router"
    )
    modelRouter = models.CharField(
        blank=True, max_length=75, verbose_name="Modelo Router"
    )
    onuId = models.FloatField(null=True, blank=True, verbose_name="Onu ID")
    servicePort = models.CharField(
        blank=True, max_length=100, verbose_name="Service Port"
    )
    ipAssigned = models.CharField(
        blank=True, max_length=100, verbose_name="IP Asignada"
    )
    ipPublic = models.BooleanField(blank=True, default=False, verbose_name="IP Public")
    servicePortGestion = models.CharField(
        blank=True, max_length=100, verbose_name="Service Port Gestion"
    )
    ipGestion = models.CharField(blank=True, max_length=100, verbose_name="IP Gestion")

    user_limit = models.IntegerField(
        blank=True, default=1, verbose_name="Límite de Usuarios hijo"
    )
    history = HistoricalRecords()
    fecha_inicio = models.DateField(
        null=True, blank=True, verbose_name="Fecha de Inicio"
    )
    fecha_nacimiento = models.DateField(
        null=True, blank=True, verbose_name="Fecha de Nacimiento"
    )

    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"

    @property
    def son_number(self):
        return UserProfile.objects.filter(
            contract=self, father=False, is_active=True
        ).count()

    def save(self, *args, **kwargs):
        actor = kwargs.pop("actor", None)
        previous_limit = self.user_limit
        was_new = self.pk is None  # Saber si es nuevo antes de guardar

        if self.planInternet:
            self.user_limit = self.planInternet.user_limit
        else:
            self.user_limit = 0

        # Validar la latitud y longitud
        if self.geolatitude is not None and not (-90 <= self.geolatitude <= 90):
            raise ValidationError(
                {"geolatitude": "La latitud debe estar entre -90 y 90 grados."}
            )

        if self.geolongitude is not None and not (-180 <= self.geolongitude <= 180):
            raise ValidationError(
                {"geolongitude": "La longitud debe estar entre -180 y 180 grados."}
            )

        super().save(*args, **kwargs)

        if previous_limit > self.user_limit:
            self.remove_exceeding_users()
            
    def create_wifi_accounts(self):
        wifi_count = self.planInternet.wifi_accounts if self.planInternet else 0
        for _ in range(wifi_count):
            WifiAccount.objects.create(contract=self, status='inactive')

    def remove_exceeding_users(self):
        users = UserProfile.objects.filter(
            usercontract__userprofile=self.userprofile, father=False
        )

        # Si el número de usuarios supera el nuevo límite, eliminarlos
        if users.count() > self.user_limit:
            excess_users = users[self.user_limit :]
            excess_users.delete()

    def __str__(self):
        return self.contract_id


auditlog.register(Contract)


class UserGroup(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Grupo")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    users = models.ManyToManyField(
        "UserProfile",
        blank=True,
        null=True,
        related_name="user_groups",
        verbose_name="Usuarios",
    )

    class Meta:
        verbose_name = "Grupo de Usuarios"
        verbose_name_plural = "Grupos de Usuarios"

    def __str__(self):
        return self.name


class UserProfile(AbstractUser):
    father = models.BooleanField(
        default=False, verbose_name="Es Usuario Principal (Padre)"
    )
    fatherstore = models.BooleanField(
        default=False, verbose_name="Es Usuario Principal (Padre) de tienda"
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        verbose_name="Contrato (solo para hijos)",
        blank=True,
        null=True,
        related_name="contract_user_profile",
    )
    birth_date = models.DateField(
        null=True, blank=True, verbose_name="Fecha de Nacimiento"
    )
    points = models.IntegerField(
        blank=True, null=True, default=0, verbose_name="Puntos Acumulados"
    )
    image_field = models.ImageField(
        blank=True,
        null=True,
        upload_to="sliders/profile",
        verbose_name="Image de Perfil",
    )
    cropping50x50 = ImageRatioField("image_field", "50x50", allow_fullsize=True)
    cropping300x300 = ImageRatioField("image_field", "300x300", allow_fullsize=True)
    update_info = models.BooleanField(
        default=False, verbose_name="Actualización de información"
    )
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    cellphone = models.CharField(
        max_length=50, default="", blank=True, null=False, verbose_name="Nro. Celular"
    )
    username = models.CharField(
        max_length=150, unique=True, verbose_name="Nombre de Usuario"
    )
    privacityandterms = models.BooleanField(
        default=False, verbose_name="Validación Términos y Condiciones"
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Correo Electrónico",
        validators=[verificar_dominio_email],
    )
    cedula = models.CharField(
        max_length=15, unique=True, blank=True, null=True, verbose_name="Cédula"
    )

    #Campos para la gestion de cuentas de hotspot
    HOTSPOT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'), 
        ('pending', 'Pending')
    ]
    hotspot_account_status = models.CharField(
        max_length=10,
        choices=HOTSPOT_STATUS_CHOICES,
        default='inactive',
        null=True,
        verbose_name="Estado de Cuenta Hotspot"
    )

    time_available = models.IntegerField(
        default=0, verbose_name="Tiempo Disponible (en minutos)"
    )

    history = HistoricalRecords()

    def get_unread_notifications(self):
        return self.notifications.filter(is_read=False, user_id=self.id).count()

    def get_cropped_url50x50(self):
        try:
            if self.image_field and self.cropping50x50:
                cropping_icon_url50x50 = get_backend().get_thumbnail_url(
                    self.image_field,
                    {
                        "size": (50, 50),
                        "box": self.cropping50x50,
                        "crop": True,
                        "detail": True,
                    },
                )
                return cropping_icon_url50x50
            return None
        except Exception as e:
            return None

    def get_cropped_url300x300(self):
        try:
            if self.image_field and self.cropping300x300:
                cropping_icon_url300x300 = get_backend().get_thumbnail_url(
                    self.image_field,
                    {
                        "size": (300, 300),
                        "box": self.cropping300x300,
                        "crop": True,
                        "detail": True,
                    },
                )
                return cropping_icon_url300x300
            return None
        except Exception as e:
            return None

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def save(self, *args, **kwargs):
        actor = kwargs.pop("actor", None)
        # Verificar si el usuario es principal
        if self.contract and not self.father:
            self.father = False
        if self.username:
            self.username = self.username.lower()
        if self.email:
            self.email = self.email.lower()
        super(UserProfile, self).save(*args, **kwargs)


auditlog.register(UserProfile)


class SpeedHistory(models.Model):
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="speeduser",
        verbose_name="Usuario",
    )
    speed = models.FloatField(default=0, verbose_name="Velocidad")
    upload = models.FloatField(default=0, verbose_name="Velocidad de Subida")
    download = models.FloatField(default=0, verbose_name="Velocidad de Bajada")
    jitter = models.FloatField(default=0, verbose_name="Latencia")
    ping = models.FloatField(default=0, verbose_name="Ping")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")

    class Meta:
        verbose_name = "Historial de Velocidad"
        verbose_name_plural = "Historial de Velocidades"


class Referral(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pendiente"),
        ("Accepted", "Aceptada"),
        ("Rejected", "Rechazada"),
    ]
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="referrals",
        verbose_name="Usuario que refiere",
    )
    referred_name = models.CharField(max_length=255, verbose_name="Nombre del referido")
    referred_email = models.EmailField(verbose_name="Correo del referido")
    referred_phone = models.CharField(
        max_length=10, verbose_name="Teléfono del referido"
    )
    status_reference = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="Pending",
        verbose_name="Estado de la Referencia",
    )
    created_at = models.DateTimeField(default=now, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Referencia"
        verbose_name_plural = "Referencias"
        ordering = ["status_reference"]

    def __str__(self):
        return f"{self.user.username} refiere a {self.referred_name} ({self.status_reference})"


class HotspotAccount(models.Model):
    TYPE_CHOICES = [
        ("Client", "Cliente"),
        ("NonClient", "No Cliente"),
    ]
    VAUCHER_CHOICES = [
        ("Unlimited", "Ilimitado"),
        ("Limited", "Limitado"),
    ]
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="hotspotaccounts",
        null=True,
        blank=True,
        verbose_name="Contrato",
    )
    username_hotspot = models.CharField(max_length=100, verbose_name="Usuario Hotspot")
    password_hotspot = models.CharField(
        max_length=200, verbose_name="Contraseña Hotspot"
    )
    date_create = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    tipo = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default="Client",
        verbose_name="Tipo de Cuenta",
    )
    vaucher = models.CharField(
        max_length=10,
        choices=VAUCHER_CHOICES,
        default="Unlimited",
        verbose_name="Váucher",
    )
    usuarioid = models.CharField(max_length=50, verbose_name="ID del Usuario")
    is_enabled = models.BooleanField(default=True, verbose_name="Cuenta habilitada")

    class Meta:
        verbose_name = "Cuenta Hotspot"
        verbose_name_plural = "Cuentas Hotspot"

    def save(self, *args, **kwargs):
        if not self.password_hotspot:
            self.password_hotspot = self.generate_password()

        if self.tipo == "NonClient" and self.contract is not None:
            raise ValueError(
                "El campo 'contract' debe ser null si 'tipo' es 'No Cliente'."
            )
        if self.tipo == "Client":
            self.vaucher = "Unlimited"

        super(HotspotAccount, self).save(*args, **kwargs)

    @staticmethod
    def generate_password(length=8):
        characters = string.ascii_letters + string.digits
        return "".join(random.choice(characters) for i in range(length))

    def __str__(self):
        return f"{self.username_hotspot} - {self.tipo} ({self.vaucher})"


class PhysicalAddress(models.Model):
    contract = models.OneToOneField(
        Contract,
        on_delete=models.CASCADE,
        related_name="physicaladdresses",
        verbose_name="Contrato",
    )
    nodo = models.CharField(max_length=100)
    cajaNAP = models.CharField(max_length=100)
    puertoNAP = models.CharField(max_length=100)
    codClienteNAP = models.CharField(max_length=100)
    equipoCore = models.CharField(max_length=100)
    equipoOLT = models.CharField(max_length=100)
    tarjetaOLT = models.CharField(max_length=100)
    puertoOLT = models.CharField(max_length=100)
    splitterSecundario = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Dirección Física"
        verbose_name_plural = "Direcciones Físicas"


class Equipe(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="equipes",
        verbose_name="Contrato",
    )
    nameTechnician = models.CharField(max_length=100, verbose_name="Nombre Técnico")
    serialOnu = models.CharField(max_length=100, verbose_name="Serial de Onu")
    modelOnu = models.CharField(max_length=100, verbose_name="Modelo de Onu")
    serialRouter = models.CharField(max_length=100, verbose_name="Serial del Router")
    modelRouter = models.CharField(max_length=100, verbose_name="Modelo del Router")

    class Meta:
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"


class WifiPoint(models.Model):
    TYPE_CHOICES = [
        ("NEGOCIO", "Negocio"),
        ("PLAZA", "Plaza"),
        ("SEMAFORO", "Semaforo"),
        ("TEATRO", "Teatro"),
    ]
    name = models.CharField(max_length=255, verbose_name="Nombre del Punto Wifi")
    latitude = models.CharField(max_length=100, verbose_name="Latitud")
    longitude = models.CharField(max_length=100, verbose_name="Longitud")
    reference = models.CharField(
        blank=True, null=True, max_length=100, verbose_name="Referencia", default=""
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="SEMAFORO",
        verbose_name="Tipo de Punto Wifi",
    )

    class Meta:
        verbose_name = "Punto Wifi"
        verbose_name_plural = "Puntos Wifi"

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Service(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Servicio")
    title = models.CharField(max_length=255, verbose_name="Titulo")
    description = models.TextField(verbose_name="Descripción del Servicio")
    image = models.ImageField(verbose_name="Imagen")

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"


class Support(models.Model):
    comment = models.TextField(verbose_name="Descripción del soporte")
    support_id = models.CharField(max_length=50, verbose_name="ID del Soporte")
    date = models.DateTimeField(
        null=True, blank=True, auto_now_add=True, verbose_name="Fecha de Creación"
    )
    image_field = models.ImageField(
        upload_to="sliders/support",
        verbose_name="Imagen",
        blank=True,
        null=True,
    )
    cropping50x50 = ImageRatioField("image_field", "50x50", allow_fullsize=True)
    is_rated = models.BooleanField(default=False, verbose_name="¿Soporte Calificado?")
    final_comment = models.TextField(
        blank=True, null=True, verbose_name="Comentario de Calificación"
    )

    class Meta:
        verbose_name = "Soporte"
        verbose_name_plural = "Soportes"

    def get_cropped_url50x50(self):
        if self.image_field and self.cropping50x50:
            cropping_icon_url50x50 = get_backend().get_thumbnail_url(
                self.image_field,
                {
                    "size": (50, 50),
                    "box": self.cropping50x50,
                    "crop": True,
                    "detail": True,
                },
            )
            return cropping_icon_url50x50
        return None

    def __str__(self):
        return f"ID: {self.support_id} - Comentario: {self.comment[:20]}"


class RatingQuestion(models.Model):
    question = models.CharField(max_length=255, verbose_name="Pregunta")
    is_active = models.BooleanField(default=True, verbose_name="Pregunta Activa")
    order = models.PositiveIntegerField(default=0, verbose_name="Orden")

    class Meta:
        verbose_name = "Pregunta de Calificación"
        verbose_name_plural = "Preguntas de Calificación"
        ordering = ["order"]

    def __str__(self):
        return self.question


class TicketRating(models.Model):
    ticket = models.ForeignKey(
        "Support", on_delete=models.CASCADE, related_name="ratings"
    )
    question = models.ForeignKey(
        RatingQuestion,
        on_delete=models.CASCADE,
        related_name="question_ratings",
        verbose_name="Pregunta",
    )
    rating = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)], verbose_name="Calificación (1-5)"
    )

    class Meta:
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"

    def __str__(self):
        return f"Calificación para {self.question} - {self.rating} estrellas"


class PaymentMethod(models.Model):
    name = models.CharField(blank=True, max_length=100, verbose_name="Nombre")
    description = models.CharField(
        blank=True, max_length=255, verbose_name="Descripción del Método de Pago"
    )
    image_field = models.ImageField(
        upload_to="sliders/paymentMethods",
        verbose_name="Imagen",
        blank=True,
        null=True,
    )
    cropping50x50 = ImageRatioField("image_field", "50x50", allow_fullsize=True)

    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"

    def __str__(self):
        return self.name

    def get_cropped_url50x50(self):
        if self.image_field and self.cropping50x50:
            cropping_icon_url50x50 = get_backend().get_thumbnail_url(
                self.image_field,
                {
                    "size": (50, 50),
                    "box": self.cropping50x50,
                    "crop": True,
                    "detail": True,
                },
            )
            return cropping_icon_url50x50
        return None


class PuntosGanados(models.Model):
    STATUS_CHOICES = [
        ("Active", "Activo"),
        ("Inactive", "Inactivo"),
    ]

    title = models.CharField(max_length=255, verbose_name="Título")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    points = models.PositiveIntegerField(verbose_name="Puntos")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="Active", verbose_name="Estado"
    )
    is_enabled = models.BooleanField(
        default=True, verbose_name="Habilitado/Inhabilitado"
    )
    linkurlpage = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Link PAGE"
    )

    class Meta:
        verbose_name = "Como Ganar Puntos"
        verbose_name_plural = "Como Ganar Puntos"

    def __str__(self):
        return f"{self.title} - {self.points} puntos"


class SliderHome(models.Model):
    image_field = models.ImageField(upload_to="sliders/home", verbose_name="Imagen")
    cropping = ImageRatioField("image_field", "355x166", allow_fullsize=True)
    title = models.CharField(max_length=255, verbose_name="Título")

    class Meta:
        verbose_name = "Slider Principal"
        verbose_name_plural = "Sliders Principales"

    def __str__(self):
        return self.title

    def get_cropped_url(self):
        if self.image_field and self.cropping:
            cropping_icon_url = get_backend().get_thumbnail_url(
                self.image_field,
                {
                    "size": (355, 166),
                    "box": self.cropping,
                    "crop": True,
                    "detail": True,
                },
            )
            return cropping_icon_url
        return None


class SliderSecond(models.Model):
    image_field = ImageCropField(
        upload_to="media/sliders/products/", verbose_name="Imagen"
    )
    cropping = ImageRatioField("image_field", "353x132", allow_fullsize=True)
    title = models.CharField(max_length=255, verbose_name="Título")

    class Meta:
        verbose_name = "Slider Secundario"
        verbose_name_plural = "Sliders Secundarios"

    def __str__(self):
        return self.title

    def get_cropped_url(self):
        if self.image_field and self.cropping:
            cropping_icon_url = get_backend().get_thumbnail_url(
                self.image_field,
                {
                    "size": (353, 132),
                    "box": self.cropping,
                    "crop": True,
                    "detail": True,
                },
            )
            return cropping_icon_url
        return None


_thread_locals = local()


def set_adjust_points_flag(value):
    _thread_locals.adjust_points = value


class Transaction(models.Model):
    STATUS_CHOICES = [
        (0, "Ingreso"),
        (1, "Egreso"),
    ]

    TYPE_CHOICES = [
        ("Promotion", "Promoción"),
        ("Product", "Producto"),
        ("Internal", "Interno"),
    ]

    TRANSACTION_STATUS_CHOICES = [
        ("Pending", "Pendiente"),
        ("Completed", "Completada"),
        ("Cancelled", "Anulada"),
    ]
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Usuario",
    )
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Transacción")
    amount = models.IntegerField(verbose_name="Nro. Puntos")
    saldo = models.IntegerField(
        verbose_name="Saldo Final de Puntos", blank=True, null=True
    )
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=0, verbose_name="Estado"
    )
    tipo = models.CharField(
        max_length=10, choices=TYPE_CHOICES, verbose_name="Tipo de Transacción"
    )
    transaction_status = models.CharField(
        max_length=15,
        choices=TRANSACTION_STATUS_CHOICES,
        default="Pending",
        verbose_name="Estado de la Transacción",
    )
    codigo_promocion = models.ForeignKey(
        Promotion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Código de Promoción",
        related_name="transaction_promotions",
    )
    codigo_producto = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Código de Producto",
        related_name="transaction_products",
    )
    descripcion = models.TextField(
        verbose_name="Descripción de la Transacción", blank=True, null=True
    )
    claim_code = models.CharField(
        max_length=6,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Código de Reclamo",
    )
    validated_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_transactions",
        verbose_name="Validado por",
    )

    class Meta:
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ["-date"]

    is_rollback = False

    def generate_unique_claim_code(self):
        """Genera un código aleatorio único para la transacción."""
        while True:
            new_code = uuid.uuid4().hex[:6].upper()
            if not Transaction.objects.filter(claim_code=new_code).exists():
                return new_code

    def rollback(self, transaction_status):
        try:
            with db_transaction.atomic():
                set_adjust_points_flag(False)

                # Lógica del rollback
                if self.status == 1:
                    self.user.points += self.amount
                elif self.status == 0:
                    self.user.points -= self.amount

                self.user.save()

                reverse_transaction = Transaction.objects.create(
                    user=self.user,
                    amount=self.amount,
                    saldo=self.user.points,
                    status=0 if self.status == 1 else 1,
                    tipo=self.tipo,
                    transaction_status="Completed",
                    descripcion=f"Reverso de la transacción {self.id} - {self.descripcion}",
                    codigo_producto=self.codigo_producto,
                    codigo_promocion=self.codigo_promocion,
                )

                # Manejo de stock y reclamos de Productos
                if self.tipo == "Product" and self.codigo_producto:
                    if self.status == 1:  # Egreso
                        self.codigo_producto.stock += 1
                        self.codigo_producto.save()

                        claim_history = UserClaimHistory.objects.filter(
                            user=self.user, product=self.codigo_producto
                        ).first()
                        if claim_history and claim_history.claims_count > 0:
                            claim_history.claims_count -= 1
                            claim_history.save()

                # Manejo de stock y reclamos de Promociones
                if self.tipo == "Promotion" and self.codigo_promocion:
                    if self.status == 1:  # Egreso
                        if self.codigo_promocion.vouchers_promotion >= 0:
                            self.codigo_promocion.vouchers_promotion += 1
                            self.codigo_promocion.save()

                        claim_history = UserClaimHistory.objects.filter(
                            user=self.user, promotion=self.codigo_promocion
                        ).first()
                        if claim_history and claim_history.claims_count > 0:
                            claim_history.claims_count -= 1
                            claim_history.save()

                self.transaction_status = "Cancelled"
                self.is_rollback = True
                self.save()
                self.is_rollback = False

                return reverse_transaction

        except Exception as e:
            print(f"Error en el rollback de la transacción {self.id}: {e}")
            raise

        finally:
            set_adjust_points_flag(True)

    def save(self, *args, **kwargs):
        is_validation = kwargs.pop("is_validation", False)

        if self.is_rollback:
            return super(Transaction, self).save(*args, **kwargs)

        if self.pk:
            instance = Transaction.objects.get(pk=self.pk)

            if instance.transaction_status == "Pending":
                if is_validation:
                    if self.transaction_status == "Completed":
                        if self.tipo == "Product" and self.codigo_producto:
                            historical_entry = (
                                HistoricalClaimProductHistory.objects.filter(
                                    producto=self.codigo_producto,
                                    user=self.user,
                                    status="Pending",
                                ).first()
                            )
                            if historical_entry:
                                historical_entry.datetime_approved = timezone.now()
                                historical_entry.status = "Completed"
                                historical_entry.save()
                        if self.tipo == "Promotion" and self.codigo_promocion:
                            historical_entrypromotion = (
                                HistoricalClaimPromotionHistory.objects.filter(
                                    promocion=self.codigo_promocion,
                                    user=self.user,
                                    store=self.codigo_promocion.store,
                                    status="Pending",
                                ).first()
                            )
                            if historical_entrypromotion:
                                historical_entrypromotion.datetime_approved = (
                                    timezone.now()
                                )
                                historical_entrypromotion.status = "Completed"
                                historical_entrypromotion.save()
                        return super(Transaction, self).save(*args, **kwargs)
                    elif self.transaction_status == "Cancelled":
                        self.rollback("Cancelled")
                        if self.tipo == "Product" and self.codigo_producto:
                            historical_entry = (
                                HistoricalClaimProductHistory.objects.filter(
                                    producto=self.codigo_producto,
                                    user=self.user,
                                    status="Pending",
                                ).first()
                            )
                            if historical_entry:
                                historical_entry.datetime_rejected = timezone.now()
                                historical_entry.status = "Cancelled"
                                historical_entry.save()
                        if self.tipo == "Promotion" and self.codigo_promocion:
                            historical_entrypromotion = (
                                HistoricalClaimPromotionHistory.objects.filter(
                                    promocion=self.codigo_promocion,
                                    user=self.user,
                                    store=self.codigo_promocion.store,
                                    status="Pending",
                                ).first()
                            )
                            if historical_entrypromotion:
                                historical_entrypromotion.datetime_rejected = (
                                    timezone.now()
                                )
                                historical_entrypromotion.status = "Cancelled"
                                historical_entrypromotion.save()
                        return super(Transaction, self).save(*args, **kwargs)
                elif self.status == 1:
                    self.rollback("Cancelled")
                    return super(Transaction, self).save(*args, **kwargs)
            elif instance.transaction_status != "Pending" and self.status == 1:
                raise ValidationError(
                    "Solo se pueden revertir transacciones pendientes."
                )

        if self.tipo == "Product":
            if not self.codigo_producto:
                raise ValueError("Debe asociarse un producto a esta transacción.")

            # Si es una transacción nueva se genera un código de reclamo único
            if not self.claim_code:
                self.claim_code = self.generate_unique_claim_code()

            if self.transaction_status == "Pending":
                if self.status == 1:  # Egreso
                    # Validar que el usuario tiene suficientes puntos y que el producto tiene stock
                    if self.user.points < self.amount:
                        raise ValueError(
                            "El usuario no tiene suficientes puntos para esta transacción."
                        )
                    if self.codigo_producto.stock <= 0:
                        raise ValueError("No hay suficiente stock para este producto.")

                    self.user.points -= self.amount
                    self.codigo_producto.stock -= 1

                    # Crear un registro en el historial
                    HistoricalClaimProductHistory.objects.create(
                        producto=self.codigo_producto,
                        user=self.user,
                        status="Pending",
                    )

                self.user.save()
                self.codigo_producto.save()
                self.saldo = self.user.points

        if self.tipo == "Promotion":
            if not self.codigo_promocion:
                raise ValueError("Debe asociarse un promoción a esta transacción.")

            # Si es una transacción nueva se genera un código de reclamo único
            if not self.claim_code:
                self.claim_code = self.generate_unique_claim_code()

            if self.transaction_status == "Pending":
                if self.status == 1:
                    # Validar que el usuario tiene suficientes puntos y que el producto tiene stock
                    if self.user.points < self.amount:
                        raise ValueError(
                            "El usuario no tiene suficientes puntos para esta transacción."
                        )
                    if self.codigo_promocion.vouchers_promotion == 0:
                        raise ValueError(
                            "No hay suficientes vouchers para esta promoción."
                        )
                    elif self.codigo_promocion.vouchers_promotion > 0:
                        self.codigo_promocion.vouchers_promotion -= 1

                    self.user.points -= self.amount

                    # Crear registro en el historial
                    historial = HistoricalClaimPromotionHistory.objects.create(
                        promocion=self.codigo_promocion,
                        user=self.user,
                        store=self.codigo_promocion.store,
                        idtransaction=self.id,
                        status="Pending",
                    )

            # Guardar los cambios en el usuario y en el producto
            self.user.save()
            self.codigo_promocion.save()
            self.saldo = self.user.points

        if (
            self.is_rollback
            and self.tipo == "Internal"
            and "Transferencia de puntos" in self.descripcion
        ):
            raise ValueError("Las transferencias de puntos no pueden ser revertidas.")

        if self.tipo == "Internal" and "Transferencia de puntos" in self.descripcion:
            self.transaction_status = "Completed"
            self.saldo = self.user.points

        return super(Transaction, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.tipo} ({self.amount})"


class SlideAction(models.Model):
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="slide_actions",
        verbose_name="Usuario",
    )
    slide_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Contador de Slides",
        help_text="Numero de slides desde la app móvil",
    )

    class Meta:
        unique_together = ("user",)
        verbose_name = "Acción del Deslizamiento"
        verbose_name_plural = "Acciones del Deslizamiento"

    def __str__(self):
        return f"User: {self.user.username}, Slides: {self.slide_count}"


class PointsCategory(models.Model):
    enabled = models.BooleanField(default=True, verbose_name="¿Habilitada?")
    name = models.CharField(
        max_length=255, unique=True, verbose_name="Forma de ganar puntos"
    )
    description = models.TextField(verbose_name="Descripción de la categoría")
    is_massive = models.BooleanField(default=False, verbose_name="Es masivo")
    massive_date = models.DateField(
        null=True, blank=True, verbose_name="Fecha de Envío"
    )
    only_privacy_terms = models.BooleanField(
        default=True, verbose_name="Solo para los usuarios con la app instalada"
    )
    only_with_fathers = models.BooleanField(
        default=False, verbose_name="Solo los usuarios Padre"
    )

    class Meta:
        verbose_name = "Categoría de Puntos"
        verbose_name_plural = "Categorías de Puntos"

    def __str__(self):
        return self.name

    def assign_massive_points(self):
        if not self.is_massive or not self.massive_date:
            return

        users = UserProfile.objects.filter(is_active=True)

        if self.only_privacy_terms:
            users = users.filter(privacityandterms=True)

        if self.only_with_fathers:
            users = users.filter(father=True)

        total_asignados = 0

        for user in users:
            contract = Contract.objects.filter(userprofile=user).first()
            if not contract or not contract.planInternet:
                continue

            config = PointsByPlanCategory.objects.filter(
                category=self, plan=contract.planInternet
            ).first()

            if config:
                if not Transaction.objects.filter(
                    user=user, descripcion__icontains=self.name, tipo="Internal"
                ).exists():
                    user.points += config.points
                    user.save()

                    Transaction.objects.create(
                        user=user,
                        amount=config.points,
                        status=0,
                        tipo="Internal",
                        transaction_status="Completed",
                        saldo=user.points,
                        descripcion=f"[Carga Masiva] {self.name}",
                    )

                    UserNotificationService.create_notification(
                        user,
                        "Puntos acreditados",
                        f"Se te han asignado {config.points} puntos por la categoría {self.name}.",
                    )

                    device = user.fcmdevice_set.first()
                    if device and device.registration_id:
                        FirebaseNotificationService.send_firebase_notification(
                            device.registration_id,
                            "Puntos acreditados",
                            f"Se te han asignado {config.points} puntos por la categoría {self.name}.",
                        )
                    total_asignados += 1

        return total_asignados


class PointsByPlanCategory(models.Model):
    category = models.ForeignKey(
        PointsCategory, on_delete=models.CASCADE, verbose_name="Categoría"
    )
    plan = models.ForeignKey(
        InternetPlan, on_delete=models.CASCADE, verbose_name="Plan de Internet"
    )
    points = models.PositiveIntegerField(verbose_name="Cantidad de Puntos")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "plan"], name="unique_category_plan"
            )
        ]
        verbose_name = "Puntos por Plan y Categoría"
        verbose_name_plural = "Puntos por Plan y Categoría"

    def __str__(self):
        return f"{self.category.name} - {self.plan.name}: {self.points} puntos"


class MassPointsLoad(models.Model):
    title = models.CharField(max_length=255, verbose_name="Título")
    assign_date = models.DateField(default=now, verbose_name="Fecha de Asignación")
    category = models.ForeignKey(
        PointsCategory,
        on_delete=models.CASCADE,
        verbose_name="Categoría de puntos",
        null=True,
        blank=True,
    )
    is_credited = models.BooleanField(default=False, verbose_name="¿Acreditado?")
    csv_file = models.FileField(
        upload_to="points/csv/", verbose_name="Archivo CSV", null=True, blank=True
    )
    error_csv = models.FileField(
        upload_to="points/errors/",
        verbose_name="Archivo de Errores",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Carga Masiva de Puntos"
        verbose_name_plural = "Cargas Masivas de Puntos"

    def __str__(self):
        return f"{self.title} - {self.assign_date}"

    def save(self, *args, **kwargs):
        self.title = self.category.name
        super().save(*args, **kwargs)

    def clean(self):
        if self.csv_file and not self.csv_file.name.endswith(".csv"):
            raise ValidationError("Solo se permiten archivos CSV.")

    def assign_points(
        self, user, points, contract=None, description="Puntos asignados"
    ):
        user.points += points
        user.save()

        # Registrar la transacción
        Transaction.objects.create(
            user=user,
            amount=points,
            status=0,
            tipo="Internal",
            transaction_status="Completed",
            saldo=user.points,
            descripcion=description,
        )

        contract_info = f"{contract.contract_id}" if contract else ""
        message = f"{contract_info}: Se te han asignado {points} puntos {description}"

        # Crear notificación
        try:
            UserNotificationService.create_notification(
                user,
                "Puntos acreditados",
                message,
            )

        except Exception as e:
            print(e)

        # Enviar notificación push
        device = user.fcmdevice_set.first()
        print(f"Dispositivo encontrado: {device}")
        if device and device.registration_id:
            try:
                test = FirebaseNotificationService.send_firebase_notification(
                    device.registration_id,
                    "Puntos acreditados",
                    message,
                    data=None,
                )
                print(f"Notificación enviada: {test}")
                print(f"Notificación enviada a {device.registration_id}")

            except Exception as e:
                print(f"Error al enviar notificación a {device.registration_id}:")
                print(e)

    def process_points(self):
        try:
            if not self.csv_file:
                raise ValidationError(
                    "Debe cargar un archivo CSV con los códigos de contrato."
                )

            csv_file = self.csv_file.open("r")
            reader = csv.reader(csv_file)
            next(reader)  # Saltar encabezado

            contratos = list(reader)
            if len(contratos) > 1000:
                raise ValidationError(
                    "El archivo CSV no puede tener más de 1000 registros."
                )

            errores = []

            for row in contratos:
                if not row:
                    continue

                contract_code = row[0].strip()
                contract = Contract.objects.filter(contract_id=contract_code).first()

                if not contract:
                    errores.append(f"Contrato no encontrado: {contract_code}")
                    continue

                usuarios = []

                if self.category.only_with_fathers:
                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not self.category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios = [usuario]
                else:
                    usuarios_qs = UserProfile.objects.filter(
                        contract=contract, is_active=True
                    )

                    if self.category.only_privacy_terms:
                        usuarios_qs = usuarios_qs.filter(privacityandterms=True)
                    usuarios = list(usuarios_qs)

                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not self.category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                        and usuario not in usuarios
                    ):
                        usuarios.append(usuario)

                if not usuarios:
                    errores.append(
                        f"No hay usuarios válidos para el contrato: {contract_code}"
                    )
                    continue

                point_config = PointsByPlanCategory.objects.filter(
                    category=self.category, plan=contract.planInternet
                ).first()

                if point_config:
                    points_to_assign = point_config.points
                else:
                    points_to_assign = 0

                    # Asignar puntos
                for user in usuarios:
                    self.assign_points(
                        user,
                        points_to_assign,
                        contract=contract,
                        description=f"{self.category.description}",
                    )

                if not point_config:
                    errores.append(
                        f"Sin configuración de puntos para el contrato: {contract_code}"
                    )
                    continue

            csv_file.close()
            self.is_credited = True
            self.save()

            # Guardar errores en CSV si hay
            if errores:
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Error"])
                for error in errores:
                    writer.writerow([error])

                output.seek(0)
                filename = f"errores_carga_{self.pk}.csv"
                self.error_csv.save(filename, ContentFile(output.read()))
                print(f"⚠️ Errores registrados y vinculados en {filename}")

        except Exception as e:
            raise ValidationError(f"Error procesando el archivo CSV: {str(e)}")

    def process_antiquity_points(self):
        try:
            if not self.csv_file:
                raise ValidationError(
                    "Debe cargar un archivo CSV con los códigos de contrato y los años."
                )

            csv_file = self.csv_file.open("r")
            reader = csv.reader(csv_file, delimiter=";")
            next(reader)

            contratos = list(reader)
            if len(contratos) > 1000:
                raise ValidationError(
                    "El archivo CSV no puede tener más de 1000 registros."
                )

            errores = []

            for row in contratos:
                if not row:
                    continue

                contract_code = row[0].strip()
                years_of_antiquity = int(row[1].strip())

                contract = Contract.objects.filter(contract_id=contract_code).first()

                if not contract:
                    errores.append(f"Contrato no encontrado: {contract_code}")
                    continue

                usuarios = []

                if self.category.only_with_fathers:
                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not self.category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios = [usuario]
                else:
                    usuarios_qs = UserProfile.objects.filter(
                        contract=contract, is_active=True
                    )

                    if self.category.only_privacy_terms:
                        usuarios_qs = usuarios_qs.filter(privacityandterms=True)
                    usuarios = list(usuarios_qs)

                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not self.category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                        and usuario not in usuarios
                    ):
                        usuarios.append(usuario)

                if not usuarios:
                    errores.append(
                        f"No hay usuarios válidos para el contrato: {contract_code}"
                    )
                    continue

                if years_of_antiquity == 1:
                    point_config = PointsByPlanCategory.objects.filter(
                        category=self.category, plan=contract.planInternet
                    ).first()
                    points_to_assign = point_config.points if point_config else 0
                elif years_of_antiquity > 1:
                    points_to_assign = 250
                else:
                    continue

                for user in usuarios:
                    self.assign_points(
                        user,
                        points_to_assign,
                        contract=contract,
                        description=f"{self.category.description}",
                    )

            csv_file.close()
            self.is_credited = True
            self.save()

            # Guardar errores en CSV si hay
            if errores:
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Error"])
                for error in errores:
                    writer.writerow([error])

                output.seek(0)
                filename = f"errores_carga_{self.pk}.csv"
                self.error_csv.save(filename, ContentFile(output.read()))
                print(f"⚠️ Errores registrados y vinculados en {filename}")

        except Exception as e:
            raise ValidationError(f"Error procesando el archivo CSV: {str(e)}")

    def process_buy_products(self):
        try:
            if not self.csv_file:
                raise ValidationError(
                    "Debe cargar un archivo CSV con los códigos de contrato y los puntos a asignar."
                )

            csv_file = self.csv_file.open("r")
            reader = csv.reader(csv_file, delimiter=";")
            next(reader)  # Saltar encabezado

            contratos = list(reader)
            if len(contratos) > 1000:
                raise ValidationError(
                    "El archivo CSV no puede tener más de 1000 registros."
                )

            errores = []

            for row in contratos:
                if not row or len(row) < 2:
                    errores.append(f"Fila incompleta: {row}")
                    continue

                contract_code = row[0].strip()
                try:
                    points_to_assign = int(row[1].strip())
                except ValueError:
                    errores.append(
                        f"Puntos inválidos para contrato {contract_code}: {row[1]}"
                    )
                    continue

                contract = Contract.objects.filter(contract_id=contract_code).first()

                if not contract:
                    errores.append(f"Contrato no encontrado: {contract_code}")
                    continue

                usuarios = []

                if self.category.only_with_fathers:
                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not self.category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios = [usuario]
                else:
                    usuarios_qs = UserProfile.objects.filter(
                        contract=contract, is_active=True
                    )

                    if self.category.only_privacy_terms:
                        usuarios_qs = usuarios_qs.filter(privacityandterms=True)
                    usuarios = list(usuarios_qs)

                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not self.category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                        and usuario not in usuarios
                    ):
                        usuarios.append(usuario)

                if not usuarios:
                    errores.append(
                        f"No hay usuarios válidos para el contrato: {contract_code}"
                    )
                    continue

                for user in usuarios:
                    self.assign_points(
                        user,
                        points_to_assign,
                        contract=contract,
                        description=f"{self.category.description}",
                    )

            csv_file.close()
            self.is_credited = True
            self.save()

            # Guardar errores en CSV si hay
            if errores:
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Error"])
                for error in errores:
                    writer.writerow([error])

                output.seek(0)
                filename = f"errores_carga_{self.pk}.csv"
                self.error_csv.save(filename, ContentFile(output.read()))
                print(f"⚠️ Errores registrados y vinculados en {filename}")

        except Exception as e:
            raise ValidationError(f"Error procesando el archivo CSV: {str(e)}")


class WifiConnectionLog(models.Model):
    user = models.ForeignKey(
        "UserProfile", on_delete=models.CASCADE, verbose_name="Usuario"
    )
    contract_code = models.CharField(max_length=20, verbose_name="Código del Contrato")
    wifi_point = models.ForeignKey(
        "WifiPoint", on_delete=models.SET_NULL, null=True, verbose_name="Punto WiFi"
    )
    created_at = models.DateTimeField(default=now, verbose_name="Fecha de conexión")

    class Meta:
        verbose_name = "Registro de Conexión WiFi"
        verbose_name_plural = "Registros de Conexiones WiFi"

    def __str__(self):
        return f"{self.user.username} conectado a {self.wifi_point} - {self.created_at}"

class WifiAccount(models.Model):
    contract = models.ForeignKey('Contract', on_delete=models.CASCADE, related_name='wifi_accounts')
    user = models.ForeignKey('UserProfile', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('active', 'Activa'),
        ('inactive', 'Disponible'),
        ('pending', 'Pendiente'),
    ])
    last_connection = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Cuenta WiFi"
        verbose_name_plural = "Cuentas WiFi"