# # Image de base Python
# FROM python:3.11-slim

# # Variables d'environnement pour Python
# ENV PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1 \
#     PIP_NO_CACHE_DIR=1 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1

# # D�finir le r�pertoire de travail
# WORKDIR /app

# # Installer les d�pendances syst�me n�cessaires pour psycopg2 et Pillow
# RUN apt-get update && apt-get install -y \
#     gcc \
#     postgresql-client \
#     libpq-dev \
#     libjpeg-dev \
#     zlib1g-dev \
#     && rm -rf /var/lib/apt/lists/*

# # Copier le fichier requirements et installer les d�pendances Python
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copier le code source
# COPY ./src /app

# # Cr�er le r�pertoire pour les fichiers statiques
# RUN mkdir -p /app/staticfiles

# # Exposer le port 8000
# EXPOSE 8000

# # Script de d�marrage
# COPY docker-entrypoint.sh /docker-entrypoint.sh
# RUN chmod +x /docker-entrypoint.sh

# ENTRYPOINT ["/docker-entrypoint.sh"]
# CMD ["gunicorn", "src.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]







# Image de base Python
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src /app

RUN mkdir -p /app/staticfiles

EXPOSE 8000

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "src.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
