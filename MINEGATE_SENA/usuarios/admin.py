from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from datetime import datetime
from .models import PerfilUsuario

class PerfilUsuarioInline(admin.StackedInline):
    """
    Permite editar el perfil directamente desde el usuario
    """
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'
    fk_name = 'user'
    fields = ('documento', 'telefono', 'direccion', 'foto_perfil', 'fecha_nacimiento', 'aprobado', 'razon_rechazo', 'fecha_aprobacion')
    readonly_fields = ('fecha_aprobacion',)

class CustomUserAdmin(UserAdmin):
    """
    Personalización del admin de usuarios
    """
    inlines = (PerfilUsuarioInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'es_aprobado', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'perfil__aprobado')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'perfil__documento')
    ordering = ('-date_joined',)
    
    def es_aprobado(self, obj):
        """Muestra el estado de aprobación del usuario"""
        if hasattr(obj, 'perfil'):
            if obj.perfil.aprobado:
                return format_html('<span style="color: green; font-weight: bold;">✓ Aprobado</span>')
            else:
                return format_html('<span style="color: red; font-weight: bold;">✗ Pendiente</span>')
        return '-'
    es_aprobado.short_description = 'Estado'

# Re-registrar UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    """
    Admin para gestionar perfiles y aprobaciones de usuarios
    """
    list_display = ('usuario', 'documento', 'telefono', 'estado_aprobacion', 'fecha_aprobacion', 'fecha_actualizacion')
    list_filter = ('aprobado', 'fecha_aprobacion', 'fecha_actualizacion')
    search_fields = ('user__username', 'documento', 'user__email', 'user__first_name', 'user__last_name')
    ordering = ('-user__date_joined',)
    actions = ['aprobar_usuarios', 'desaprobar_usuarios']
    readonly_fields = ('fecha_actualizacion', 'fecha_aprobacion', 'info_usuario')
    
    fieldsets = (
        ('Información del Usuario', {
            'fields': ('info_usuario', 'documento')
        }),
        ('Datos de Contacto', {
            'fields': ('telefono', 'direccion')
        }),
        ('Información Personal', {
            'fields': ('foto_perfil', 'fecha_nacimiento')
        }),
        ('Control de Acceso', {
            'fields': ('aprobado', 'razon_rechazo', 'fecha_aprobacion'),
            'description': 'Aquí puedes aprobar o rechazar el acceso del usuario al sistema'
        }),
        ('Auditoría', {
            'fields': ('fecha_actualizacion',),
            'classes': ('collapse',)
        }),
    )
    
    def usuario(self, obj):
        """Muestra el nombre de usuario"""
        return f"{obj.user.get_full_name() or obj.user.username}"
    usuario.short_description = 'Usuario'
    
    def estado_aprobacion(self, obj):
        """Muestra el estado de aprobación con colores"""
        if obj.aprobado:
            return format_html(
                '<span style="color: white; background-color: green; padding: 5px 10px; border-radius: 3px; font-weight: bold;">✓ APROBADO</span>'
            )
        else:
            return format_html(
                '<span style="color: white; background-color: red; padding: 5px 10px; border-radius: 3px; font-weight: bold;">✗ PENDIENTE</span>'
            )
    estado_aprobacion.short_description = 'Estado'
    
    def info_usuario(self, obj):
        """Muestra información completa del usuario"""
        user = obj.user
        return format_html(
            '<div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">'
            '<strong>Usuario:</strong> {}<br>'
            '<strong>Email:</strong> {}<br>'
            '<strong>Nombre Completo:</strong> {}<br>'
            '<strong>Fecha de Registro:</strong> {}<br>'
            '</div>',
            user.username,
            user.email,
            user.get_full_name() or 'No especificado',
            user.date_joined.strftime('%d/%m/%Y %H:%M')
        )
    info_usuario.short_description = 'Información del Usuario'
    
    def aprobar_usuarios(self, request, queryset):
        """Acción para aprobar usuarios"""
        updated = queryset.update(aprobado=True, fecha_aprobacion=datetime.now())
        self.message_user(request, f'{updated} usuario(s) aprobado(s) exitosamente.')
    aprobar_usuarios.short_description = '✓ Aprobar usuarios seleccionados'
    
    def desaprobar_usuarios(self, request, queryset):
        """Acción para desaprobar usuarios"""
        updated = queryset.update(aprobado=False, fecha_aprobacion=None)
        self.message_user(request, f'{updated} usuario(s) desaprobado(s) exitosamente.', level='WARNING')
    desaprobar_usuarios.short_description = '✗ Desaprobar usuarios seleccionados'


