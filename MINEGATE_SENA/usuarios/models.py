from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class PerfilUsuario(models.Model):
    """
    Modelo para extender la información del usuario
    Relacionado 1:1 con el modelo User de Django
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='perfil'
    )
    
    documento = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Número de documento de identidad"
    )
    
    telefono = models.CharField(
        max_length=15, 
        blank=True,
        help_text="Número de teléfono"
    )
    
    direccion = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Dirección de residencia"
    )
    
    foto_perfil = models.ImageField(
        upload_to='perfiles/', 
        blank=True, 
        null=True,
        help_text="Foto de perfil del usuario"
    )
    
    fecha_nacimiento = models.DateField(
        null=True, 
        blank=True,
        help_text="Fecha de nacimiento"
    )
    
    aprobado = models.BooleanField(
        default=False,
        help_text="El usuario solo puede acceder al sistema si está aprobado por el administrador"
    )
    
    razon_rechazo = models.TextField(
        blank=True,
        null=True,
        help_text="Razón por la cual se rechazó el acceso del usuario"
    )
    
    fecha_aprobacion = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Fecha en que se aprobó el acceso del usuario"
    )
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"
        ordering = ['-user__date_joined']
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    def get_nombre_completo(self):
        """Retorna el nombre completo del usuario"""
        return f"{self.user.first_name} {self.user.last_name}"


# Señales para crear/actualizar perfil automáticamente
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Crea automáticamente un perfil cuando se crea un usuario
    Solo si el perfil no existe ya (evita duplicados con el formulario de registro)
    """
    if created:
        # Solo crear si no existe ya un perfil para este usuario
        if not hasattr(instance, 'perfil'):
            try:
                PerfilUsuario.objects.get(user=instance)
            except PerfilUsuario.DoesNotExist:
                # Solo crear para usuarios que no vienen del registro
                # (superusuarios creados desde consola, etc.)
                pass

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    """
    Guarda el perfil cuando se guarda el usuario
    """
    if hasattr(instance, 'perfil'):
        instance.perfil.save()