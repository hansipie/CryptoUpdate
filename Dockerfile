# Utilisez une image Python officielle comme image de base
FROM python:3-slim

RUN apt update && apt upgrade -y

# Create a new user and group
RUN groupadd -r docker -g 1000 && useradd -r -g docker -u 1000 -m -d /home/docker docker

# Set the home directory ownership and permissions
RUN chown -R docker:docker /home/docker && chmod -R 755 /home/docker

# Add directoty to the PATH
ENV PATH="/home/docker/.local/bin:${PATH}"

# Switch to the new user
USER docker

# create application's directory
RUN mkdir /home/docker/app

# Définissez le répertoire de travail
WORKDIR /home/docker/app

# Exposez le port 8080
EXPOSE 8080

# Copiez les fichiers de configuration et d'installation du projet dans le répertoire de travail
COPY requirements.in .

# Installez les dépendances Python nécessaires
RUN pip install --upgrade pip
RUN pip install pip-tools && pip-compile --output-file requirements.txt requirements.in
RUN pip install --no-cache-dir -r requirements.txt

# Copiez le reste des fichiers du projet dans le répertoire de travail
COPY . .

# Définissez la commande pour exécuter votre application
CMD streamlit run app.py --server.port 8080
