import os
import shutil
import stat
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Genera una copia de seguridad PostgreSQL en formato custom "
        "(.dump/.backup) dentro de la carpeta backups."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--filename",
            default="",
            help=(
                "Nombre del archivo de salida (solo nombre, sin ruta). "
                "Si no se indica, se genera automaticamente con fecha y hora."
            ),
        )
        parser.add_argument(
            "--extension",
            choices=["dump", "backup"],
            default="dump",
            help="Extension del archivo de salida.",
        )

    def handle(self, *args, **options):
        db_conf = settings.DATABASES.get("default", {})
        engine = db_conf.get("ENGINE", "")

        if "postgresql" not in engine:
            raise CommandError(
                "El comando backupdb solo funciona con PostgreSQL."
            )

        backup_dir = Path(settings.BASE_DIR) / "backups"
        self._asegurar_directorio_backup(backup_dir)

        extension = options["extension"]
        nombre_archivo = self._resolver_nombre_archivo(
            options.get("filename", ""),
            extension,
        )

        backup_path = (backup_dir / nombre_archivo).resolve()

        pg_dump = self._resolver_binario_postgres("pg_dump")

        cmd = [
            pg_dump,
            "-F",
            "c",
            "-f",
            str(backup_path),
            "-d",
            str(db_conf.get("NAME", "")),
        ]

        if db_conf.get("HOST"):
            cmd.extend(["-h", str(db_conf["HOST"])])
        if db_conf.get("PORT"):
            cmd.extend(["-p", str(db_conf["PORT"])])
        if db_conf.get("USER"):
            cmd.extend(["-U", str(db_conf["USER"])])

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
            if backup_path.exists():
                backup_path.unlink(missing_ok=True)
            detalle = (resultado.stderr or resultado.stdout or "").strip()
            raise CommandError(
                "No se pudo generar la copia de seguridad con pg_dump. "
                f"Detalle: {detalle}"
            )

        self._asegurar_permisos_archivo(backup_path)

        self.stdout.write(
            self.style.SUCCESS(
                f"Copia generada correctamente: {backup_path.name}"
            )
        )
        self.stdout.write(f"Ruta: {backup_path}")

    def _resolver_nombre_archivo(self, filename, extension):
        if not filename:
            marca_tiempo = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            return f"sicam_backup_{marca_tiempo}.{extension}"

        nombre = Path(filename).name
        if nombre != filename:
            raise CommandError(
                "El parametro --filename solo acepta nombre de archivo, no rutas."
            )

        sufijo = Path(nombre).suffix.lower()
        if sufijo not in {".dump", ".backup"}:
            raise CommandError(
                "El archivo de salida debe terminar en .dump o .backup."
            )

        return nombre

    def _asegurar_directorio_backup(self, backup_dir):
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            if os.name == "nt":
                os.chmod(backup_dir, stat.S_IREAD | stat.S_IWRITE)
            else:
                os.chmod(
                    backup_dir,
                    stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR,
                )
        except OSError as exc:
            self.stderr.write(
                f"Advertencia: no se pudieron ajustar permisos del directorio backups: {exc}"
            )

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
