"""Entrada sencilla para ejecutar el taxímetro en terminal."""

import sys
from taximetro.__main__ import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "cli", *sys.argv[1:]]
    main()
