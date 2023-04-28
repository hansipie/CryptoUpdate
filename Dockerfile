# Utilisez une image Python officielle comme image de base
FROM python:3.10-slim

# Définissez le répertoire de travail
WORKDIR /app

# Copiez les fichiers de configuration et d'installation du projet dans le répertoire de travail
COPY requirements.txt .

# Installez les dépendances Python nécessaires
RUN pip install --no-cache-dir -r requirements.txt

# Copiez le reste des fichiers du projet dans le répertoire de travail
COPY . .

# Exposez le port sur lequel votre application s'exécutera (si nécessaire)
# EXPOSE 8000

# Définissez la commande pour exécuter votre application
CMD ["python", "main.py"]
