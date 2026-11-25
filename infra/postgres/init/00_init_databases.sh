# 00_init_databases.sh
#
# Description : crée les deux bases de JobCompass et leurs tables.
# Règles      : $POSTGRES_DB        = vraies données ;
#               ${POSTGRES_DB}_dev  = passages de test (is_test) et tests
#                                     automatiques, isolés des vraies données.
#               Les deux bases reçoivent exactement les mêmes scripts
#               (schema/*.sql, dans l'ordre) : mêmes schémas, mêmes tables.
#               Lu (source) par l'entrypoint de Postgres au premier démarrage
#               (volume vide) uniquement ; les scripts de schema/ ne sont pas
#               lancés directement par l'entrypoint (sous-dossier).

set -e

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "create database \"${POSTGRES_DB}_dev\""

for database in "$POSTGRES_DB" "${POSTGRES_DB}_dev"; do
    for script in /docker-entrypoint-initdb.d/schema/*.sql; do
        echo "init: $script -> $database"
        psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$database" -f "$script"
    done
done
