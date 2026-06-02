# =============================================================
# Stage 1 — Build du frontend React / Vite
# =============================================================
FROM node:22-slim AS ui-builder

WORKDIR /build/ui
COPY ui/package*.json ui/package-lock.json* ./
RUN npm ci --prefer-offline

COPY ui/ ./
# En prod, l'app appelle des URL relatives (/parse, /health…)
# — le proxy Vite ne sert qu'en développement.
RUN npm run build
# Résultat : /build/ui/dist/


# =============================================================
# Stage 2 — Runtime Python / FastAPI
# =============================================================
FROM python:3.11-slim AS runtime

LABEL maintainer="France Air – Solutions Habitat"
LABEL org.opencontainers.image.description="INVENIO – Fiche de sélection PAC/GEG"

# ── Dépendances système (WeasyPrint) ──────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libfontconfig1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dépendances Python (couche cachée séparément) ────────────
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# ── Code source backend ───────────────────────────────────────
COPY src/ ./src/
COPY tools/ ./tools/

# ── Frontend buildé depuis le Stage 1 ────────────────────────
COPY --from=ui-builder /build/ui/dist/ ./ui/dist/

# ── Sécurité : utilisateur non-root ──────────────────────────
RUN adduser --disabled-password --gecos "" invenio
USER invenio

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 2 workers suffisent pour un usage interne (ajuster si besoin)
CMD ["uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
