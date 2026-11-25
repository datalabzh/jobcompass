#!/usr/bin/env bash
# run_dbt.sh
#
# Description : construit les tables d'analyse (dbt build) à partir de ce que
#               les sites ont déposé. Lancé à la main ou par supercronic
#               (jobcompass.cron), une fois, après les passages des sites.
# Règles      : mode test (--target dev) ou full (--target real) : voir
#               common.sh. Une seule ligne cron : deux dbt build en même temps se
#               gêneraient. dbt n'attend pas la fin des sites : un site en retard
#               arrive dans les marts au passage suivant.

set -uo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

log "début : dbt build, target $TARGET"
uv run "${ENV_FILE[@]}" --package jobcompass-dbt \
  dbt build --project-dir dbt --profiles-dir dbt --target "$TARGET" \
  || { code=$?; log "dbt : erreur $code"; exit $code; }
log "fin"
