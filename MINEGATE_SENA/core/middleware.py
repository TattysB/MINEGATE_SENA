from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.contrib.sessions.exceptions import SessionInterrupted
from django.shortcuts import resolve_url


class GracefulSessionInterruptedMiddleware:
    """
    Convierte SessionInterrupted en una redirección al login.

    Evita que una sesión eliminada concurrentemente muestre traceback
    cuando Django intenta guardarla al finalizar la respuesta.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except SessionInterrupted:
            login_url = resolve_url(settings.LOGIN_URL)
            return redirect_to_login(
                request.get_full_path(),
                login_url=login_url,
            )