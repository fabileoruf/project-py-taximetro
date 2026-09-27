"""Una contraseña con hash scrypt y una clave de sesión aleatoria."""

from getpass import getpass
import json
import os
from pathlib import Path
import secrets

from werkzeug.security import check_password_hash, generate_password_hash


def create_credentials(directory, password):
    if not isinstance(password, str) or len(password) < 10 or len(password) > 256:
        raise ValueError("La contraseña debe tener entre 10 y 256 caracteres.")
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    credentials = {"password_hash": generate_password_hash(password),
                   "session_secret": secrets.token_hex(32)}
    # Creación exclusiva: nunca sobrescribir las credenciales de otro arranque.
    fd = os.open(directory / "credentials.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(credentials, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return credentials


def load_credentials(directory):
    path = Path(directory) / "credentials.json"
    if not path.exists():
        raise ValueError("Configura tu contraseña con: python -m taximetro setup")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("password_hash") or not data.get("session_secret"):
        raise ValueError("Archivo de credenciales inválido.")
    return data


def verify(credentials, password):
    return (isinstance(password, str) and 0 < len(password) <= 256
            and check_password_hash(credentials["password_hash"], password))


def setup(directory):
    if (Path(directory) / "credentials.json").exists():
        print("Contraseña ya configurada.")
        return
    print("Crea una contraseña de 10 caracteres como mínimo. No se mostrará al escribir.")
    while True:
        password = getpass("Contraseña: ")
        confirmation = getpass("Repite la contraseña: ")
        if password != confirmation:
            print("Las contraseñas no coinciden.")
            continue
        try:
            create_credentials(directory, password)
            print("Acceso configurado. Se ha guardado únicamente el hash de la contraseña.")
            return
        except ValueError as error:
            print(error)
