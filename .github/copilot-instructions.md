# Instructions globales pour le projet CryptoUpdate

## Présentation
CryptoUpdate est une application de gestion de portefeuilles crypto, d'import/export de données et de visualisation graphique, développée en Python.

## Structure du projet
- `app.py` : Point d'entrée principal.
- `app_pages/` : Pages de l'application (accueil, portefeuilles, graphiques, opérations, import, paramètres, tests).
- `modules/` : Modules métiers (traitement AI, configuration, outils, etc.).
- `modules/database/` : Accès et gestion de la base de données.
- `data/` : Fichiers de base de données et sauvegardes.
- `tests/` : Tests unitaires.
- `Dockerfile`, `compose.yml` : Conteneurisation et orchestration Docker.
- `requirements.txt`, `pyproject.toml`, `uv.lock` : Dépendances Python (gérées avec uv).

## Installation
### Prérequis
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (gestionnaire de dépendances rapide)
- Docker (optionnel)

### Installation locale
```sh
uv init
uv sync
```

### Lancement de l'application
```sh
uv run streamlit run app.py
```

### Utilisation avec Docker
```sh
docker compose up
```

## Tests
Lancez les tests unitaires avec :
```sh
uv pip install pytest
pytest tests/
```

## Bonnes pratiques
- Respectez la structure des dossiers.
- Documentez vos fonctions et modules.
- Ajoutez des tests pour chaque nouvelle fonctionnalité.
- Utilisez des branches pour le développement.

## Contribution
1. Forkez le repo et clonez-le.
2. Créez une branche pour vos modifications.
3. Faites vos changements et ajoutez des tests.
4. Soumettez une Pull Request.

## Support
Pour toute question, ouvrez une issue sur GitHub ou contactez l'auteur.
