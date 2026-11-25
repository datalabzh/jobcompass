# common.sh
#
# Description : ce que partagent run_site.sh et run_dbt.sh : se placer à la
#               racine du dépôt, choisir le mode (test ou full), écrire les logs.
# Règles      : lu par source, jamais lancé seul.
#               PIPELINE_MODE=test (défaut) : passages limités, base jobcompass_dev,
#               dbt --target dev. PIPELINE_MODE=full : --full, base jobcompass,
#               dbt --target real. Par défaut, tout va en test (sécurité du projet).
#               Priorité : variable donnée à la commande, puis orchestration/.env
#               (propre à chaque machine, non versionné, modèle .env.example),
#               puis test.
#               Définit : MODE, FULL (options des commandes Python), TARGET (dbt),
#               ENV_FILE (infra/.env pour dbt s'il existe ; dans le conteneur, les
#               variables viennent de docker compose) et la fonction log.

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2

GIVEN_MODE="${PIPELINE_MODE:-}"
# shellcheck source=/dev/null
[[ -f orchestration/.env ]] && source orchestration/.env
MODE="${GIVEN_MODE:-${PIPELINE_MODE:-test}}"

case "$MODE" in
  test) FULL=(); TARGET="dev" ;;
  full) FULL=(--full); TARGET="real" ;;
  *) echo "PIPELINE_MODE doit valoir test ou full (reçu : $MODE)" >&2
     exit 2 ;;
esac

ENV_FILE=()
[[ -f infra/.env ]] && ENV_FILE=(--env-file infra/.env)

log() { echo "$(date '+%F %T') [$(basename "$0" .sh)] $*" >&2; }
