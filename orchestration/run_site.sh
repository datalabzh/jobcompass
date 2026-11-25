#!/usr/bin/env bash
# run_site.sh
#
# Description : passage complet d'un site : extraction, puis normalisation de ses
#               fiches. Lancé à la main ou par supercronic (jobcompass.cron), une
#               ligne par site.
# Règles      : run_site.sh <site>, <site> = nom de son dossier dans extraction/
#               (ex. jobup). Mode test ou full : voir common.sh.
#               Extraction en code 1 (une catégorie en échec) : on normalise quand
#               même, car is_active ne tient compte que des passages réussis ; le
#               script finit en code 1. Toute autre erreur (2 : configuration,
#               3 : arrêt imprévu) arrête le passage du site avec son code.
#               Un site n'attend ni ne gêne les autres : chacun a sa ligne cron.
#               dbt n'est pas lancé ici : run_dbt.sh, à heure fixe, pour tous les
#               sites.

set -uo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

SITE="${1:-}"
if [[ -z "$SITE" ]]; then
  echo "usage : run_site.sh <site>   (ex. run_site.sh jobup)" >&2
  exit 2
fi

status=0
log "début : site $SITE, mode $MODE"

log "1/2 extraction"
uv run --package jobcompass-entrypoints jobcompass-extraction run "$SITE" "${FULL[@]}"
code=$?
case $code in
  0) ;;
  1) log "extraction : au moins une catégorie en échec, on continue"; status=1 ;;
  *) log "extraction : erreur $code, arrêt"; exit $code ;;
esac

log "2/2 normalisation"
uv run --package jobcompass-entrypoints jobcompass-normalization run "$SITE" "${FULL[@]}" \
  || { code=$?; log "normalisation : erreur $code, arrêt"; exit $code; }

log "fin : site $SITE, statut $status"
exit $status
