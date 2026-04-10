import os
import shutil
import stat
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


ALLOWED_BACKUP_EXTENSIONS = {".dump", ".backup"}


class Command(BaseCommand):
    help = (
        "Restaura una copia de seguridad PostgreSQL (.dump/.backup) "
        "desde la carpeta backups."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Nombre del archivo de backup dentro de la carpeta backups.",
        )
        parser.add_argument(
            "--target",
            choices=["default", "test"],
            default="default",
            help="Base destino: principal (default) o base de prueba (test).",
        )
        parser.add_argument(
            "--test-db-name",
            default="test_restore",
            help="Nombre de base para pruebas cuando --target=test.",
        )
        parser.add_argument(
            "--test-db-user",
            default="",
            help="Usuario para base de pruebas (opcional).",
        )
        parser.add_argument(
            "--test-db-password",
            default="",
            help="Contrasena para base de pruebas (opcional).",
        )
        parser.add_argument(
            "--test-db-host",
            default="",
            help="Host para base de pruebas (opcional).",
        )
        parser.add_argument(
            "--test-db-port",
            default="",
            help="Puerto para base de pruebas (opcional).",
        )

    def handle(self, *args, **options):
        archivo_backup = self._resolver_archivo_backup(options["file"])
        db_conf = self._resolver_configuracion_destino(options)

        pg_restore = self._resolver_binario_postgres("pg_restore")

        cmd = [
            pg_restore,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "-d",
            str(db_conf["NAME"]),
        ]

        if db_conf.get("HOST"):
            cmd.extend(["-h", str(db_conf["HOST"])])
        if db_conf.get("PORT"):
            cmd.extend(["-p", str(db_conf["PORT"])])
        if db_conf.get("USER"):
            cmd.extend(["-U", str(db_conf["USER"])])

        cmd.append(str(archivo_backup))

        env = os.environ.copy()
        if db_conf.get("PASSWORD"):
            env["PGPASSWORD"] = str(db_conf["PASSWORD"])

        resultado = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        if resultado.returncode != 0:
            detalle = (resultado.stderr or resultado.stdout or "").strip()

            if options["target"] == "test":
                detalle = (
                    f"{detalle} "
                    "Asegura que la base exista. Ejemplo: createdb test_restore"
                )

            raise CommandError(
                "No se pudo restaurar la copia de seguridad con pg_restore. "
                f"Detalle: {detalle}"
            )

        self._asegurar_permisos_archivo(archivo_backup)

        etiqueta_destino = "principal" if options["target"] == "default" else "pruebas"
        self.stdout.write(
            self.style.SUCCESS(
                f"Restauracion completada en base {etiqueta_destino}: {db_conf['NAME']}"
            )
        )
        self.stdout.write(f"Archivo usado: {archivo_backup.name}")

        if options["target"] == "test":
            self.stdout.write(
                "Validacion sugerida: psql -d "
                f"{db_conf['NAME']} -c \"\\dt\""
            )

    def _resolver_archivo_backup(self, file_option):
        backup_dir = (Path(settings.BASE_DIR) / "backups").resolve()
        backup_dir.mkdir(parents=True, exist_ok=True)

        nombre = (file_option or "").strip()
        if not nombre:
            raise CommandError("Debes indicar un archivo con --file.")

        if Path(nombre).name != nombre:
            raise CommandError(
                "Por seguridad, --file solo acepta nombres de archivo (sin rutas)."
            )

        extension = Path(nombre).suffix.lower()
        if extension not in ALLOWED_BACKUP_EXTENSIONS:
            raise CommandError("Solo se permiten archivos .dump o .backup.")

        archivo = (backup_dir / nombre).resolve()
        if backup_dir not in archivo.parents:
            raise CommandError("Ruta de backup invalida.")

        if not archivo.exists() or not archivo.is_file():
            raise CommandError(
                f"El archivo {nombre} no existe en la carpeta backups."
            )

        return archivo

    def _resolver_configuracion_destino(self, options):
        default_db = settings.DATABASES.get("default", {})
        engine = default_db.get("ENGINE", "")

        if "postgresql" not in engine:
            raise CommandError(
                "El comando restoredb solo funciona con PostgreSQL."
            )

        if options["target"] == "default":
            destino = {
                "NAME": default_db.get("NAME", ""),
                "USER": default_db.get("USER", ""),
                "PASSWORD": default_db.get("PASSWORD", ""),
                "HOST": default_db.get("HOST", ""),
                "PORT": default_db.get("PORT", ""),
            }
        else:
            destino = {
                "NAME": options.get("test_db_name", "") or "test_restore",
                "USER": options.get("test_db_user", "") or default_db.get("USER", ""),
                "PASSWORD": (
                    options.get("test_db_password", "")
                    or default_db.get("PASSWORD", "")
                ),
                "HOST": options.get("test_db_host", "") or default_db.get("HOST", ""),
                "PORT": options.get("test_db_port", "") or default_db.get("PORT", ""),
            }

        if not destino.get("NAME"):
            raise CommandError("No se encontro nombre de base de datos destino.")

        return destino

    def _asegurar_permisos_archivo(self, backup_path):
        try:
            if os.name == "nt":
                os.chmod(backup_path, stat.S_IREAD | stat.S_IWRITE)
            else:
                os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError as exc:
            self.stderr.write(
                f"Advertencia: no se pudieron ajustar permisos del archivo: {exc}"
            )

    def _resolver_binario_postgres(self, binary_name):
        postgres_bin_dir = getattr(settings, "POSTGRES_BIN_DIR", "")
        candidatos = [binary_name]

        if os.name == "nt" and not binary_name.lower().endswith(".exe"):
            candidatos.append(f"{binary_name}.exe")

        if postgres_bin_dir:
            for candidato in candidatos:
                posible = Path(postgres_bin_dir) / candidato
                if posible.exists():
                    return str(posible)

        postgres_bin_env = os.environ.get("POSTGRES_BIN_DIR", "")
        if postgres_bin_env:
            for candidato in candidatos:
                posible = Path(postgres_bin_env) / candidato
                if posible.exists():
                    return str(posible)

        for candidato in candidatos:
            encontrado = shutil.which(candidato)
            if encontrado:
                return encontrado

        if os.name == "nt":
            for bin_dir in self._rutas_bin_postgres_windows():
                for candidato in candidatos:
                    posible = bin_dir / candidato
                    if posible.exists():
                        return str(posible)

        raise CommandError(
            f"No se encontro {binary_name}. Agrega PostgreSQL al PATH, define POSTGRES_BIN_DIR en settings.py o variable de entorno, o instala PostgreSQL localmente."
        )

    def _rutas_bin_postgres_windows(self):
        """Detecta rutas tipicas de PostgreSQL en Windows (Program Files)."""
        bases = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramW6432", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]

        vistas = []
        for base in bases:
            if not base:
                continue

            raiz_pg = Path(base) / "PostgreSQL"
            if not raiz_pg.exists() or not raiz_pg.is_dir():
                continue

            versiones = [
                d for d in raiz_pg.iterdir() if d.is_dir() and d.name.isdigit()
            ]
            versiones.sort(key=lambda d: int(d.name), reverse=True)

            for version_dir in versiones:
                bin_dir = version_dir / "bin"
                if bin_dir.exists() and bin_dir.is_dir():
                    vistas.append(bin_dir)

        return vistas
