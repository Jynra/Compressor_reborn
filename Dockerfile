# Dockerfile
FROM node:18-alpine AS frontend-builder

# Construire le frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Image finale avec Python
FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libfontconfig1 \
    libxrender1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code backend
COPY backend/ ./backend/

# Copier le frontend buildé
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Créer les répertoires nécessaires
RUN mkdir -p /app/uploads /app/compressed

# Exposer le port
EXPOSE 5000

# Variables d'environnement
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production

# Commande de démarrage
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]