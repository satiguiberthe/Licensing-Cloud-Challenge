from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.


class HistoriqueModel(models.Model):
    created_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Créé le"
    )

    updated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Mis à jour le"
    )

    deleted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Supprimé le"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_historiques'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_historiques'
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deleted_historiques'
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name="Slug"
    )

    def save(self):
        if not self.slug:
            current_time = timezone.now().strftime("%Y%m%d%HHh%MMM%SSSS")
            self.slug = str(current_time)
        
        super().save()