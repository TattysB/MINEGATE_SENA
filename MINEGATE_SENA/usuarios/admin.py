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
    fields = ('documento', 'telefono', 'direccion', 'foto_perfil', 'fecha_nacimiento')

class CustomUserAdmin(UserAdmin):
    """
    Personalización del admin de usuarios
    """
    inlines = (PerfilUsuarioInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'estado_cuenta', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'perfil__documento')
    ordering = ('-date_joined',)
    
    def estado_cuenta(self, obj):
        """Muestra el estado de la cuenta del usuario"""
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Activo</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">✗ Inactivo</span>')
    estado_cuenta.short_description = 'Estado'

# Re-registrar UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    """
    Admin para gestionar perfiles de usuarios
    """
    list_display = ('usuario', 'documento', 'telefono', 'estado_cuenta', 'fecha_actualizacion')
    list_filter = ('user__is_active', 'fecha_actualizacion')
    search_fields = ('user__username', 'documento', 'user__email', 'user__first_name', 'user__last_name')
    ordering = ('-user__date_joined',)
    actions = ['activar_usuarios', 'desactivar_usuarios']
    readonly_fields = ('fecha_actualizacion', 'info_usuario')
    
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
        ('Auditoría', {
            'fields': ('fecha_actualizacion',),
            'classes': ('collapse',)
        }),
    )
    
    def usuario(self, obj):
        """Muestra el nombre de usuario"""
        return f"{obj.user.get_full_name() or obj.user.username}"
    usuario.short_description = 'Usuario'
    
    def estado_cuenta(self, obj):
        """Muestra el estado de la cuenta con colores"""
        if obj.user.is_active:
            return format_html(
                '<span style="color: white; background-color: green; padding: 5px 10px; border-radius: 3px; font-weight: bold;">✓ ACTIVO</span>'
            )
        else:
            return format_html(
                '<span style="color: white; background-color: red; padding: 5px 10px; border-radius: 3px; font-weight: bold;">✗ INACTIVO</span>'
            )
    estado_cuenta.short_description = 'Estado'
    
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
    
    def activar_usuarios(self, request, queryset):
        """Acción para activar usuarios"""
        for perfil in queryset:
            perfil.user.is_active = True
            perfil.user.save()
        self.message_user(request, f'{queryset.count()} usuario(s) activado(s) exitosamente.')
    activar_usuarios.short_description = '✓ Activar usuarios seleccionados'
    
    def desactivar_usuarios(self, request, queryset):
        """Acción para desactivar usuarios"""
        for perfil in queryset:
            perfil.user.is_active = False
            perfil.user.save()
        self.message_user(request, f'{queryset.count()} usuario(s) desactivado(s) exitosamente.', level='WARNING')
    desactivar_usuarios.short_description = '✗ Desactivar usuarios seleccionados'


