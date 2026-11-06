#!/bin/sh
set -eu
# El entrypoint oficial ejecuta esto SOLO al inicializar un volumen vacio.
# El usuario POSTGRES_USER puede crear una DB aislada para pruebas.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -tc \
  "SELECT 1 FROM pg_database WHERE datname = 'novarent_test'" | grep -q 1 || \
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c 'CREATE DATABASE novarent_test'
