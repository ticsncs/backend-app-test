from django.db import models
from image_cropping import ImageRatioField


# Create your models here.
class DynamicContent(models.Model):
    CONTENT_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
    ]
    key = models.CharField(max_length=100, unique=True, verbose_name="Clave",
                           help_text="Identificador único para el contenido")
    content_type = models.CharField(max_length=10,
                                    verbose_name="Tipo de contenido",
                                    choices=CONTENT_TYPES,
                                    default='text')
    text = models.TextField(null=True, blank=True, verbose_name="Texto",
                            help_text="Contenido de texto para la app")
    image = models.ImageField(upload_to='app_content/images/',
                              verbose_name="Imagen", null=True,
                              blank=True, help_text="Imagen para la app")
    image_cropping = ImageRatioField("image", "800x500",
                                     allow_fullsize=True)
    updated_at = models.DateTimeField(auto_now=True,
                                      help_text="Ultima fecha de actualización",
                                      verbose_name="Fecha de Actualización")

    class Meta:
        verbose_name = "Contenido Dinámico"
        verbose_name_plural = "Contenidos Dinámicos"
        unique_together = ['key']

    def __str__(self):
        return f"{self.key} ({self.content_type})"
