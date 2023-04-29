# Utilisez une image Python officielle comme image de base
FROM python:3.10-slim

# Create a new user and group
RUN groupadd -r docker -g 1000 && useradd -r -g docker -u 1000 -m -d /home/docker docker

# Set the home directory ownership and permissions
RUN chown -R docker:docker /home/docker && chmod -R 755 /home/docker

# Switch to the new user
USER docker

# Définissez le répertoire de travail
WORKDIR /home/docker

# Add directoty to the PATH
ENV PATH="/home/docker/.local/bin:${PATH}"

# Copiez les fichiers de configuration et d'installation du projet dans le répertoire de travail
COPY requirements.txt .

# Installez les dépendances Python nécessaires
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiez le reste des fichiers du projet dans le répertoire de travail
COPY . .

# Exposez le port sur lequel votre application s'exécutera (si nécessaire)
# EXPOSE 8000

# Définissez la commande pour exécuter votre application
CMD ["python", "main.py"]
