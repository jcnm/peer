# Plan de Développement Détaillé de Peer Omniscient

## Introduction

Ce document présente un plan de développement pragmatique et itératif pour obtenir un assistant de développement **Peer Omniscient**, conformément à l'architecture évoluée proposée et aux technologies recommandées. Chaque étape inclut une validation des choix technologiques et architecturaux pour garantir l'utilisation des meilleures solutions adaptées aux besoins spécifiques de Peer.

**Objectif final** : Un assistant de développement omniscient (Peer) fonctionnant localement, avec feedback vocal, analyse continue du contexte, et une architecture hexagonale robuste et extensible.

**Principes directeurs** :
- **Itératif et progressif** : Construire et tester par étapes.
- **Validation continue** : Vérifier les choix technologiques et architecturaux à chaque étape clé.
- **Priorité au local** : Assurer le fonctionnement sans dépendances cloud obligatoires.
- **Qualité du code** : Intégrer les meilleures pratiques (tests, linting, typage) dès le début.
- **Simplicité pragmatique** : Choisir les outils les plus adaptés et les plus simples pour le besoin, en évitant la sur-ingénierie (ex: pas de LangGraph/AG2 si non justifié).

## Prérequis

- Le code avec les 4 interfaces de bases.
- Environnement de développement Python 3.10+ configuré.
- Accès aux outils de base (Git, éditeur de code : VSC).

## Phases de Développement

### Phase 1 : Configuration et Nettoyage Initial (Durée : 1-2 semaines)

**Objectif** : Mettre en place les outils de qualité, nettoyer le code existant et préparer la structure du projet pour la refonte.

| Étape | Action | Technologies/Outils | Validation | Livrable |
|-------|--------|---------------------|------------|----------|
| 1.1 | **Mise en place des outils de qualité** | **Ruff** (0.3.0), **Mypy** (1.8.0), **pytest** (8.0.0), **pre-commit** (3.5.0) | **Validation** : Ruff est confirmé comme le linter/formateur le plus rapide et complet en 2025, remplaçant avantageusement Flake8, Black, isort. Mypy reste le standard pour le typage statique. Pytest est le framework de test le plus puissant. Pre-commit est essentiel pour l'intégration CI/CD. | Configuration `pyproject.toml` (Ruff, Mypy), `pytest.ini`, `.pre-commit-config.yaml`. |
| 1.2 | **Nettoyage initial du code** | Ruff, Mypy | Appliquer Ruff et Mypy sur tout le code existant pour corriger les erreurs de style, de formatage et de typage de base. | Code base formaté et linté. |
| 1.3 | **Configuration de base de pytest** | pytest | Mettre en place la structure de base des tests et quelques tests initiaux pour valider la configuration. | Structure `/tests` avec configuration de base. |
| 1.4 | **Refonte de la structure de répertoires** | Structure de projet Python moderne | Organiser le code source (`src/peer/`) en prévision de l'architecture hexagonale (créer des répertoires vides pour `domain`, `application`, `infrastructure`). | Nouvelle structure de répertoires. |

### Phase 2 : Refonte du Noyau - Architecture Hexagonale (Durée : 3-4 semaines)

**Objectif** : Mettre en place les fondations de l'architecture hexagonale, définir les interfaces (ports) et commencer à migrer la logique métier principale.

| Étape | Action | Technologies/Outils | Validation | Livrable |
|-------|--------|---------------------|------------|----------|
| 2.1 | **Définition des Ports du Domaine** | Python Protocols | Définir les interfaces clés (ports) pour les services principaux du domaine (ex: `LLMServicePort`, `CodeAnalysisPort`, `WorkflowExecutionPort`) dans `src/peer/domain/ports/`. | Fichiers de ports définis. |
| 2.2 | **Implémentation initiale du Domaine** | Logique métier Python | Commencer à déplacer la logique métier existante (workflows, analyse de base) vers la couche `src/peer/domain/services/`, en respectant les ports définis. | Services de domaine initiaux implémentés. |
| 2.3 | **Mise en place de l'Injection de Dépendances** | **Dependency Injector** (4.41.0) | **Validation** : Dependency Injector est choisi pour sa légèreté, sa performance et sa facilité d'utilisation par rapport à d'autres frameworks DI Python. Configurer le conteneur DI pour gérer les dépendances entre services. | Conteneur DI configuré, services injectés. |
| 2.4 | **Mise en place du Framework Applicatif** | **FastAPI** (0.110.0) | **Validation** : FastAPI est confirmé comme le meilleur choix pour Peer grâce à sa performance, son support asynchrone natif, sa validation Pydantic et sa documentation OpenAPI, essentiels pour l'API REST et potentiellement la TUI. Configurer l'application FastAPI de base dans `src/peer/application/`. | Application FastAPI de base fonctionnelle. |

### Phase 3 : Couche Infrastructure - Adaptateurs Initiaux (Durée : 4-6 semaines)

**Objectif** : Implémenter les adaptateurs essentiels pour connecter le domaine aux technologies externes (LLM local, système de fichiers, commandes, parseurs).

| Étape | Action | Technologies/Outils | Validation | Livrable |
|-------|--------|---------------------|------------|----------|
| 3.1 | **Adaptateur LLM Local** | **Ollama** (0.2.0), `httpx` | **Validation** : Ollama est choisi pour sa facilité d'utilisation et sa gestion de modèles locaux. Implémenter l'adaptateur (`src/peer/infrastructure/llm/ollama_adapter.py`) pour communiquer avec l'API Ollama locale. | Adaptateur LLM fonctionnel avec tests. |
| 3.2 | **Adaptateur Système de Fichiers** | `pathlib` (std) | Implémenter l'adaptateur pour les opérations de fichiers en utilisant la bibliothèque standard `pathlib`. | Adaptateur de fichiers fonctionnel avec tests. |
| 3.3 | **Adaptateur de Commandes** | `subprocess` (std) | Implémenter un adaptateur sécurisé pour exécuter des commandes externes. | Adaptateur de commandes fonctionnel avec tests. |
| 3.4 | **Adaptateur Parseurs** | **Tree-sitter** (0.21.0), `tree-sitter-python` | **Validation** : Tree-sitter reste la référence pour le parsing incrémental robuste. Intégrer Tree-sitter pour l'analyse syntaxique via un adaptateur dédié. | Adaptateur de parsing fonctionnel avec tests. |
| 3.5 | **Intégration des Adaptateurs** | Dependency Injector | Connecter les adaptateurs aux services du domaine via l'injection de dépendances. | Services du domaine utilisant les adaptateurs. |

### Phase 4 : Interfaces Utilisateur et Persistance (Durée : 4-6 semaines)

**Objectif** : Développer les interfaces utilisateur (CLI, TUI, API) et mettre en place la persistance des sessions.

| Étape | Action | Technologies/Outils | Validation | Livrable |
|-------|--------|---------------------|------------|----------|
| 4.1 | **Refonte de la CLI** | **Typer** (0.9.0) | **Validation** : Typer est préféré à Click pour son intégration avec FastAPI et son typage. Migrer l'interface CLI existante vers Typer. | Nouvelle CLI fonctionnelle. |
| 4.2 | **Développement de la TUI** | **Textual** (0.52.1) | **Validation** : Textual est le framework TUI le plus avancé en 2025, offrant une expérience riche. Implémenter les écrans principaux de la TUI. | Interface TUI de base fonctionnelle. |
| 4.3 | **Implémentation de l'API REST** | **FastAPI** (0.110.0), **Pydantic** (2.5.2) | Développer les endpoints API principaux pour l'intégration IDE/externe. | API REST documentée (OpenAPI) et fonctionnelle. |
| 4.4 | **Mise en place de la Persistance** | **SQLAlchemy** (2.0.25), **SQLite** (std), **Alembic** (1.13.0) | **Validation** : SQLAlchemy + SQLite est la solution la plus simple et robuste pour la persistance locale. Alembic est standard pour les migrations. Configurer la base de données et les modèles pour les sessions. | Système de persistance fonctionnel avec migrations. |
| 4.5 | **Mise en place du Cache** | **Redis** (7.2.4), `redis-py` | **Validation** : Redis est la référence pour le cache performant, facilement déployable localement. Intégrer Redis pour le cache des opérations coûteuses. | Système de cache fonctionnel. |

### Phase 5 : Système de Plugins et Modes (Durée : 2-3 semaines)

**Objectif** : Implémenter le système de plugins pour rendre les modes de fonctionnement extensibles.

| Étape | Action | Technologies/Outils | Validation | Livrable |
|-------|--------|---------------------|------------|----------|
| 5.1 | **Intégration du Gestionnaire de Plugins** | **Pluggy** (1.5.0) | **Validation** : Pluggy est choisi pour sa légèreté et sa flexibilité par rapport à Stevedore. Intégrer Pluggy dans la couche application. | Gestionnaire de plugins intégré. |
| 5.2 | **Définition de l'Interface Plugin** | Python Protocols | Définir l'interface standard pour les plugins de mode. | Interface de plugin définie. |
| 5.3 | **Migration des Modes Existants** | Pluggy | Migrer les modes 'architecte' et 'code' existants en plugins. | Modes existants fonctionnant comme plugins. |
| 5.4 | **Implémentation des Nouveaux Modes** | Pluggy | Développer les plugins pour les nouveaux modes (reviewer, testeur, PMO, etc.). | Nouveaux modes implémentés comme plugins. |

### Phase 6 : Service Peer Assistant Omniscient (Durée : 4-6 semaines)

**Objectif** : Développer le cœur de Peer : le service transversal d'assistance omnisciente.

| Étape | Action | Technologies/Outils | Validation | Livrable |
|-------|--------|---------------------|------------|----------|
| 6.1 | **Adaptateur Éditeur de Code** | API VSCode/PyCharm | Développer les adaptateurs pour recevoir les événements des IDE (modifications, sélection, etc.). | Adaptateurs IDE fonctionnels (communication basique). |
| 6.2 | **Analyseur de Contexte** | Tree-sitter, LLM (Ollama) | Implémenter la logique d'analyse du contexte de développement (fichier ouvert, fonction, projet). | Service d'analyse contextuelle. |
| 6.3 | **Service de Détection de Mode** | Logique personnalisée | Implémenter la logique pour déterminer le mode le plus approprié selon le contexte. | Service de détection de mode. |
| 6.4 | **Intégration du Feedback Vocal** | **Piper** (1.3.0), **SpeechRecognition** (3.10.0) | **Validation** : Piper est confirmé comme le meilleur TTS local. SpeechRecognition est un standard pour l'ASR. Intégrer l'adaptateur TTS et la reconnaissance vocale (pour commandes vocales futures). | Service de feedback vocal fonctionnel. |
| 6.5 | **Orchestration du Peer Assistant** | Architecture événementielle, `asyncio` | Mettre en place le service principal du Peer Assistant qui orchestre l'analyse continue, la détection de mode et le feedback. | Service Peer Assistant fonctionnel. |

### Phase 7 : Intégrations et Finalisation (Durée : 3-4 semaines)

**Objectif** : Finaliser les intégrations IDE/VCS, ajouter la documentation et peaufiner l'ensemble.

| Étape | Action | Technologies/Outils | Validation | Livrable |
|-------|--------|---------------------|------------|----------|
| 7.1 | **Intégration VCS** | **GitPython** (3.1.40), **pre-commit** (3.5.0) | **Validation** : GitPython est mature pour l'interaction Git. Pre-commit est standard pour les hooks. Implémenter l'intégration avec Git et les hooks pre-commit. | Intégration VCS fonctionnelle. |
| 7.2 | **Finalisation des Extensions IDE** | API VSCode/PyCharm | Améliorer les extensions IDE pour une intégration profonde (affichage feedback, actions contextuelles). | Extensions IDE complètes. |
| 7.3 | **Tests d'Intégration et E2E** | pytest | Écrire des tests d'intégration couvrant les flux complets. | Suite de tests d'intégration robuste. |
| 7.4 | **Documentation** | **mkdocs-material** (9.5.0) | **Validation** : MkDocs avec Material est une solution moderne et simple pour la documentation. Rédiger la documentation utilisateur et développeur. | Documentation complète générée. |
| 7.5 | **Packaging et Distribution** | `pyproject.toml`, `build`, `twine` | Préparer le package pour la distribution (ex: via PyPI). | Package distribuable. |

## Validation Continue

À la fin de chaque phase (et idéalement à chaque étape clé), une revue de conception et de code doit être effectuée pour :
- **Valider les choix architecturaux** : Sont-ils toujours pertinents ? Existe-t-il de meilleures alternatives apparues récemment ?
- **Valider les choix technologiques** : La technologie choisie répond-elle aux attentes ? Est-elle performante et maintenable dans le contexte de Peer ?
- **Vérifier la conformité locale** : L'étape réalisée maintient-elle la capacité de fonctionnement local ?
- **Analyser la qualité du code** : Le code respecte-t-il les standards définis (linting, typage, tests) ?

## Conclusion du Plan

En suivant ces étapes itératives et en validant continuellement les choix, il est possible de construire un outil robuste, performant et aligné avec la vision initiale, tout en garantissant un fonctionnement local optimal.
