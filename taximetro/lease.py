"""Una instancia por carpeta de datos (macOS/Linux/Docker)."""

from contextlib import contextmanager
import fcntl
from pathlib import Path


@contextmanager
def application_lock(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".app.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Ya hay un taxímetro usando esta carpeta de datos.") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
