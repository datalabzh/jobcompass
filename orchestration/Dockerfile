# Image du conteneur pipeline : la chaîne JobCompass planifiée par supercronic.
#
# Construite par docker compose (service pipeline de infra/docker-compose.yml),
# contexte = racine du dépôt. Fichiers exclus : Dockerfile.dockerignore.
# Contenu : Python 3.12, uv, toutes les briques (sans les dépendances de dev),
# les packages dbt, et supercronic qui lit orchestration/jobcompass.cron.
# orchestration/ est monté en volume par docker compose : changer l'heure ou le
# mode ne demande qu'un redémarrage, pas de reconstruire l'image.
# Versions fixées (uv, supercronic) : build reproductible. Pour monter de version,
# changer la version et les sommes SHA1 publiées sur la page de la release
# (https://github.com/aptible/supercronic/releases).

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.10 /uv /uvx /usr/local/bin/

# tzdata : heure locale du fichier cron (TZ) ; curl : téléchargement de supercronic
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tzdata \
    && rm -rf /var/lib/apt/lists/*

ARG SUPERCRONIC_VERSION=v0.2.51
ARG TARGETARCH
RUN case "${TARGETARCH:-amd64}" in \
        amd64) sha1=1692066e350a88ff4d7d6474fe3c7a6c41ec5e89 ;; \
        arm64) sha1=9d4c2000493215a1898502b2fc2dada3e8ea8c7a ;; \
        *) echo "architecture non prise en charge : $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && curl -fsSLo /usr/local/bin/supercronic \
       "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH:-amd64}" \
    && echo "${sha1}  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod +x /usr/local/bin/supercronic

# UV_NO_SYNC : uv run utilise l'environnement installé ici, sans rien réinstaller
# à chaque passage. UV_PYTHON_DOWNLOADS=never : le Python de l'image.
ENV TZ=Europe/Zurich \
    UV_NO_SYNC=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY . .

RUN uv sync --all-packages --frozen --no-dev \
    && uv run --package jobcompass-dbt dbt deps --project-dir dbt --profiles-dir dbt

CMD ["supercronic", "/app/orchestration/jobcompass.cron"]
