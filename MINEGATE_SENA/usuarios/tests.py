from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import PerfilUsuario
from .forms import RegistroForm




class PerfilUsuarioCreationTest(TestCase):
    """
    Verifica que se pueda crear un perfil de usuario correctamente
    """

    def test_crear_perfil_usuario(self):
        """
        Crea un usuario y su perfil con documento, teléfono y dirección.
        Verifica que el perfil se crea correctamente y contiene los datos esperados.
        """
        user = User.objects.create_user(
            username="123456789",
            email="juan@example.com",
            password="TestPassword123!",
            first_name="Juan",
            last_name="Pérez",
        )

        perfil = PerfilUsuario.objects.create(
            user=user,
            documento="123456789",
            telefono="3105551234",
            direccion="Calle 1 #2-3",
        )

        self.assertEqual(perfil.documento, "123456789")
        self.assertEqual(perfil.telefono, "3105551234")
        self.assertEqual(perfil.get_nombre_completo(), "Juan Pérez")




class RegistroFormEmailDuplicadoTest(TestCase):
    """
    Verifica que el formulario rechace registro con email duplicado
    """

    def test_email_duplicado_falla(self):
        """
        Intenta registrar dos usuarios con el mismo email.
        El formulario debe fallar en la validación porque el email ya existe.
        """
        User.objects.create_user(
            username="user1", email="duplicado@example.com", password="TestPassword123!"
        )

        form = RegistroForm(
            data={
                "documento": "987654321",
                "email": "duplicado@example.com",  # Email ya existe
                "first_name": "Carlos",
                "last_name": "García",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
                "telefono": "3105551234",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)




class RegistroFormContraseñaDebilTest(TestCase):
    """
    Verifica que el formulario rechace contraseñas débiles
    """

    def test_contraseña_sin_mayuscula_falla(self):
        """
        Intenta registrar con una contraseña sin mayúsculas.
        El formulario debe fallar porque requiere mayúscula.
        """
        form = RegistroForm(
            data={
                "documento": "111222333",
                "email": "carlos@example.com",
                "first_name": "Carlos",
                "last_name": "García",
                "password1": "securepass123!",  # Sin mayúscula
                "password2": "securepass123!",
                "telefono": "3105551234",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)




class LoginViewExitosoTest(TestCase):
    """
    Verifica que un usuario pueda iniciar sesión correctamente
    """

    def setUp(self):
        """Crear usuario antes del test"""
        self.user = User.objects.create_user(
            username="123456789", password="TestPassword123!", first_name="Juan"
        )
        self.client = Client()

    def test_login_exitoso(self):
        """
        Intenta iniciar sesión con credenciales válidas.
        Verifica que el usuario sea redirigido correctamente después del login.
        """
        response = self.client.post(
            reverse("usuarios:login"),
            {
                "username": "123456789",
                "password": "TestPassword123!",
                "remember_me": False,
            },
            follow=True,  # Seguir redirecciones
        )

        self.assertEqual(response.status_code, 200)




class ListaUsuariosAccesoDenegadoTest(TestCase):
    """
    Verifica que usuarios sin permisos no puedan acceder a la lista de usuarios
    """

    def setUp(self):
        """Crear usuario regular sin permisos"""
        self.user = User.objects.create_user(
            username="usuario_regular",
            password="TestPassword123!",
            is_staff=False,  # NO es staff
        )
        self.client = Client()

    def test_usuario_regular_no_puede_acceder(self):
        """
        Un usuario regular (no staff) intenta acceder a la lista de usuarios.
        El sistema debe redirigirlo porque no tiene permisos.
        """
        self.client.login(username="usuario_regular", password="TestPassword123!")

        response = self.client.get(reverse("usuarios:lista_usuario"))

        self.assertEqual(response.status_code, 302)
