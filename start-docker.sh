#!/bin/sh
set -eu
cd "$(dirname "$0")"
docker compose build
if [ -t 0 ]; then
    docker compose run --rm --no-deps app python -m taximetro setup
else
    docker compose run --rm --no-deps -T app python -m taximetro setup
fi
docker compose up -d --wait
printf '\nTaxiTech disponible en http://localhost:%s\n' "${TAXIMETRO_PORT:-8080}"
