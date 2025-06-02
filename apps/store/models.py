from django.urls import reverse
import json
from django.db import models
from django.conf import settings
import qrcode
from io import BytesIO
from django.core.files import File
from image_cropping import ImageRatioField, ImageCropField
from image_cropping.utils import get_backend
from simple_history.models import HistoricalRecords
from auditlog.registry import auditlog
from django.core.files.base import ContentFile

class Store(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre de la tienda")
    latitude = models.CharField(max_length=100, blank=True, null=True, verbose_name="Latitud")
    longitude = models.CharField(max_length=100, blank=True, null=True, verbose_name="Longitud")
    email = models.EmailField(blank=True, null=True, verbose_name="Email Tienda")
    telephone = models.CharField(blank=True, null=True, max_length=15, verbose_name="Teléfono")
    state = models.CharField(blank=True, null=True,max_length=100, verbose_name="Provincia o Ciudad")
    RUC_number = models.CharField(blank=True, null=True, max_length=13, unique=True, verbose_name="RUC del Propietario")
    is_enabled = models.BooleanField(blank=True, null=True, default=True, verbose_name="Habilitado")
    categoria = models.CharField(max_length=100, blank=True, null=True, verbose_name="Categoría")
    qr_code = models.ImageField(upload_to='qr_codes/stores', blank=True, null=True, verbose_name="Código QR")
    wifi_ssid = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre de la red Wi-Fi (SSID)")
    wifi_password = models.CharField(max_length=255, blank=True, null=True, verbose_name="Contraseña Wi-Fi")
    wifi_security = models.CharField(
        max_length=10,
        choices=[("WPA", "WPA"), ("WPA2", "WPA2"), ("WEP", "WEP"), ("nopass", "Sin contraseña")],
        default="WPA2",
        verbose_name="Seguridad Wi-Fi"
    )
    qr_wifi = models.ImageField(upload_to="qr_wificodes/", blank=True, null=True, verbose_name="Código QR Wi-Fi")
    history = HistoricalRecords()

    def generate_qr_code(self):
        if not self.wifi_ssid:
            return

        wifi_data = f"WIFI:T:{self.wifi_security};S:{self.wifi_ssid};"
        if self.wifi_password:
            wifi_data += f"P:{self.wifi_password};"
        wifi_data += ";;"

        qr = qrcode.make(wifi_data)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        self.qr_wifi.save(f"wifi_{self.name}.png", ContentFile(buffer.getvalue()), save=False)

    class Meta:
        verbose_name = "Tienda"
        verbose_name_plural = "Tiendas"

    def save(self, *args, **kwargs):
        actor = kwargs.pop('actor', None)

        if not self.qr_code:
            qr_data_dict = {
                "store_id": self.id,
                "store_name": self.name,
                "email": self.email,
                "telephone": self.telephone,
            }
            qr_data_json = json.dumps(qr_data_dict)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data_json)
            qr.make(fit=True)

            img = qr.make_image(fill='black', back_color='white')
            buffer = BytesIO()
            img.save(buffer)
            buffer.seek(0)
            self.qr_code.save(f'{self.name}_store_qr.png', File(buffer), save=False)

        if self.wifi_ssid:
            self.generate_qr_code()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StoreUser(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_users",
        verbose_name="Usuario"
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="storeuser_users",
        verbose_name="Tienda"
    )
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        actor = kwargs.pop('actor', None)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Usuario de Tienda"
        verbose_name_plural = "Usuarios de Tienda"

class Promotion(models.Model):
    AUTHORIZATION_CHOICES = [
        ('Pending', 'Pendiente'),
        ('Authorized', 'Autorizada'),
        ('Rejected', 'Rechazada'),
    ]
    store = models.ForeignKey('Store', on_delete=models.CASCADE, related_name="promotions", verbose_name="Tienda")
    title = models.CharField(max_length=255, verbose_name="Título")
    description = models.TextField(verbose_name="Descripción")
    created_up = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Fecha de Creación")
    points_required = models.IntegerField(blank=True, null=True, default=0, verbose_name="Puntos Requeridos")
    vouchers_promotion = models.IntegerField(default=0, verbose_name="Vouchers (-1 para ilimitados)", help_text="-1 significa ilimitado. Cualquier valor >= 0 indica stock limitado.")
    authorize_promotion = models.CharField(max_length=10, choices=AUTHORIZATION_CHOICES, default='Pending', verbose_name="Estado de Autorización")
    is_enabled = models.BooleanField(default=False, verbose_name="Habilitado")
    start_datetime = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Inicio")
    end_datetime = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Fin")
    max_claims_per_user = models.PositiveIntegerField(
        blank=True,
        null=True,
        default=1,
        verbose_name="Máximo de reclamos por usuario",
        help_text="Número máximo de veces que un usuario puede reclamar esta promoción."
    )
    image_field = models.ImageField(blank=True, null=True, upload_to='promotions', verbose_name="Imagen Referencial")
    cropping50x50 = ImageRatioField("image_field", "50x50", allow_fullsize=True)
    cropping300x300 = ImageRatioField("image_field", "300x300", allow_fullsize=True)
    history = HistoricalRecords()

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

    def get_cropped_url300x300(self):
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

    def save(self, *args, **kwargs):
        actor = kwargs.pop('actor', None)

        # Actualizar is_enabled basado en vouchers_promotion
        if self.vouchers_promotion == 0:
            self.is_enabled = False

        super().save(*args,**kwargs)

    class Meta:
        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"

    def __str__(self):
        return f"{self.title} - {self.store.name}"

class Product(models.Model):
    STATUS_CHOICES = [
        ("Available", "Disponible"),
        ("Discontinued", "Descontinuado"),
    ]
    code_producto = models.CharField(max_length=50, unique=True, verbose_name="Código del Producto")
    title = models.CharField(max_length=255, verbose_name="Título")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock Disponible")
    update_create = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name="Última Actualización")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Available", verbose_name="Estado")
    points_required = models.IntegerField(blank=True, null=True, default=0, verbose_name="Puntos Requeridos")
    is_enabled = models.BooleanField(default=True, verbose_name="Habilitado")
    max_claims_per_user = models.PositiveIntegerField(
        blank=True,
        null=True,
        default=1,
        verbose_name="Máximo de reclamos por usuario",
        help_text="Número máximo de veces que un usuario puede reclamar este producto."
    )
    image_field = models.ImageField(blank=True, null=True, upload_to='products', verbose_name="Imagen")
    cropping50x50 = ImageRatioField("image_field", "50x50", allow_fullsize=True)
    cropping300x300 = ImageRatioField("image_field", "300x300", allow_fullsize=True)
    history = HistoricalRecords()

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

    def get_cropped_url300x300(self):
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

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-update_create']

    def save(self, *args, **kwargs):
        actor = kwargs.pop('actor', None)

        if self.stock <= 0:
            self.is_enabled = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.code_producto}"

class UserClaimHistory(models.Model):
    user = models.ForeignKey("clients.UserProfile", on_delete=models.CASCADE, verbose_name="Usuario")
    promotion = models.ForeignKey(Promotion, null=True, blank=True, on_delete=models.CASCADE, verbose_name="Promoción")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE, verbose_name="Producto")
    claims_count = models.PositiveIntegerField(default=0, verbose_name="Conteo de Reclamos")
    last_claim_date = models.DateTimeField(auto_now=True, verbose_name="Última fecha de Reclamo")

    class Meta:
        unique_together = ('user', 'promotion', 'product')
        verbose_name = "Historial de reclamo por usuario"
        verbose_name_plural = "Historial de reclamos por usuario"
        ordering = ["-last_claim_date"]

class HistoricalClaimProductHistory(models.Model):
    producto = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="historical_productclaims", verbose_name="Producto"
    )
    user = models.ForeignKey(
        "clients.UserProfile", on_delete=models.CASCADE, related_name="historical_product_claims", verbose_name="Usuario"
    )
    datetime_created = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    datetime_approved = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de aprobación")
    datetime_rejected = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de rechazo")
    status = models.CharField(
        max_length=15,
        choices=[
            ("Pending", "Pendiente"),
            ("Completed", "Completado"),
            ("Cancelled", "Cancelado"),
        ],
        default="Pending",
        verbose_name="Estado",
    )

    class Meta:
        verbose_name = "Historial de reclamo de producto"
        verbose_name_plural = "Historial de reclamos de productos"
        ordering = ["-datetime_created"]

    def __str__(self):
        return f"{self.user.username} - {self.producto.title} ({self.status})"


class HistoricalClaimPromotionHistory(models.Model):
    promocion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="historical_promotionclaims", verbose_name="Promoción"
    )
    user = models.ForeignKey(
        "clients.UserProfile", on_delete=models.CASCADE, related_name="historical_promotions_claims", verbose_name="Usuario"
    )
    store = models.ForeignKey(
        Store, on_delete=models.CASCADE, related_name="historical_claims", verbose_name="Tienda"
    )
    datetime_created = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    idtransaction = models.IntegerField(null=True, blank=True, verbose_name="ID de la Transacción")
    datetime_approved = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de aprobación")
    datetime_rejected = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de rechazo")
    status = models.CharField(
        max_length=15,
        choices=[
            ("Pending", "Pendiente"),
            ("Completed", "Completado"),
            ("Cancelled", "Cancelado"),
        ],
        default="Pending",
        verbose_name="Estado",
    )

    class Meta:
        verbose_name = "Historial de reclamo de promoción"
        verbose_name_plural = "Historial de reclamos de promociones"
        ordering = ["-datetime_created"]

    def __str__(self):
        return f"{self.user.username} - {self.promocion.title} ({self.status})"


auditlog.register(Store)
auditlog.register(StoreUser)
auditlog.register(Promotion)
auditlog.register(Product)