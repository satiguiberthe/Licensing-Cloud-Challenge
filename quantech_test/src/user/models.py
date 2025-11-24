from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


class UserProfileModel(AbstractUser):
    """Modèle utilisateur personnalisé"""
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    # Champs requis pour AbstractUser personnalisé
    REQUIRED_FIELDS = ['email']  # username est déjà requis par défaut

    class Meta:
        db_table = 'user_profile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.username}"