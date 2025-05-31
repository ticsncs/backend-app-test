from django.db import models


class PdfContent(models.Model):
    filename = models.CharField(max_length=255)
    content = models.TextField()

    class Meta:
        verbose_name = 'Contenido PDF'
        verbose_name_plural = 'Contenidos PDF'

    def __str__(self):
        return self.filename
