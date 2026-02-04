from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from usuarios.models import PerfilUsuario

# Create your views here.

def index (request):
    return render (request, 'core/index.html')


@login_required(login_url='usuarios:login')
def panel_administrativo (request):
    """
    Panel administrativo principal
    Incluye gestión de permisos solo para superusuarios
    """
    # Verificar que el usuario esté aprobado (excepto superusuarios)
    if not request.user.is_superuser:
        if not hasattr(request.user, 'perfil') or not request.user.perfil.aprobado:
            messages.error(request, 'No tienes permiso para acceder al sistema.')
            return redirect('usuarios:login')
    
    context = {
        'es_superusuario': request.user.is_superuser
    }
    
    # Si es superusuario, agregar datos para gestión de permisos
    if request.user.is_superuser:
        # Obtener filtros
        filtro_actual = request.GET.get('filtro', 'todos')
        buscar = request.GET.get('buscar', '')
        
        # Obtener todos los perfiles (excluyendo superusuarios)
        perfiles = PerfilUsuario.objects.select_related('user').exclude(user__is_superuser=True)
        
        # Aplicar filtros
        if filtro_actual == 'aprobados':
            perfiles = perfiles.filter(aprobado=True)
        elif filtro_actual == 'pendientes':
            perfiles = perfiles.filter(aprobado=False, razon_rechazo__isnull=True)
        elif filtro_actual == 'rechazados':
            perfiles = perfiles.filter(aprobado=False, razon_rechazo__isnull=False)
        
        # Aplicar búsqueda
        if buscar:
            perfiles = perfiles.filter(
                Q(user__username__icontains=buscar) |
                Q(user__email__icontains=buscar) |
                Q(user__first_name__icontains=buscar) |
                Q(user__last_name__icontains=buscar) |
                Q(documento__icontains=buscar)
            )
        
        # Ordenar por fecha de registro
        perfiles = perfiles.order_by('-user__date_joined')
        
        # Estadísticas
        total_usuarios = PerfilUsuario.objects.exclude(user__is_superuser=True).count()
        usuarios_aprobados = PerfilUsuario.objects.filter(aprobado=True).exclude(user__is_superuser=True).count()
        usuarios_pendientes = PerfilUsuario.objects.filter(aprobado=False, razon_rechazo__isnull=True).exclude(user__is_superuser=True).count()
        usuarios_rechazados = PerfilUsuario.objects.filter(aprobado=False, razon_rechazo__isnull=False).exclude(user__is_superuser=True).count()
        
        context.update({
            'perfiles': perfiles,
            'filtro_actual': filtro_actual,
            'buscar': buscar,
            'total_usuarios': total_usuarios,
            'usuarios_aprobados': usuarios_aprobados,
            'usuarios_pendientes': usuarios_pendientes,
            'usuarios_rechazados': usuarios_rechazados,
        })
    
    return render (request, 'core/panel_administrativo.html', context)
