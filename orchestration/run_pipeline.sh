#!/usr/bin/env bash
# run_pipeline.sh
#
# Description : enchaîne les trois étapes de la chaîne JobCompass pour jobup :
#               extraction, normalisation, puis dbt build. Lancé à la main ou par
#               supercronic (voir jobcompass.cron).
# Règles      : PIPELINE_MODE=test (défaut) : passages limités, base jobcompass_dev,
#               dbt --target dev. PIPELINE_MODE=full : --full, base jobcompass,
#               dbt --target real. Par défaut, tout va en test (sécurité du projet).
#               Priorité : variable donnée à la commande, puis orchestration/.env
#               (propre à chaque machine, non versionné, modèle .env.example),
#               puis test.
#               Extraction en code 1 (une catégorie en échec) : on continue, car
#               is_active ne tient compte que des passages réussis ; le script
#               finit quand même en code 1. Toute autre erreur arrête la chaîne
#               avec son code.
#               infra/.env est passé à dbt seulement s'il existe : dans le
#               conteneur, les variables viennent de docker compose.
#               Toujours lancé depuis la racine du dépôt (le script s'y place).

set -uo pipefail

cd "$(dirname "$0")/.." || exit 2

SITE="jobup"
GIVEN_MODE="${PIPELINE_MODE:-}"
# shellcheck source=/dev/null
[[ -f orchestration/.env ]] && source orchestration/.env
MODE="${GIVEN_MODE:-${PIPELINE_MODE:-test}}"

case "$MODE" in
  test) FULL=(); TARGET="dev" ;;
  full) FULL=(--full); TARGET="real" ;;
  *) echo "run_pipeline: PIPELINE_MODE doit valoir test ou full (reçu : $MODE)" >&2
     exit 2 ;;
esac

ENV_FILE=()
[[ -f infra/.env ]] && ENV_FILE=(--env-file infra/.env)

log() { echo "$(date '+%F %T') [pipeline] $*" >&2; }

status=0
log "début : site $SITE, mode $MODE"

log "1/3 extraction"
uv run --package jobcompass-entrypoints jobcompass-extraction run "$SITE" "${FULL[@]}"
code=$?
case $code in
  0) ;;
  1) log "extraction : au moins une catégorie en échec, on continue"; status=1 ;;
  *) log "extraction : erreur $code, arrêt"; exit $code ;;
esac

log "2/3 normalisation"
uv run --package jobcompass-entrypoints jobcompass-normalization run "$SITE" "${FULL[@]}" \
  || { code=$?; log "normalisation : erreur $code, arrêt"; exit $code; }

log "3/3 dbt build (target $TARGET)"
uv run "${ENV_FILE[@]}" --package jobcompass-dbt \
  dbt build --project-dir dbt --profiles-dir dbt --target "$TARGET" \
  || { code=$?; log "dbt : erreur $code, arrêt"; exit $code; }

log "fin : statut $status"
exit $status
