# Guide d'Architecture de Peer

## Vue d'Ensemble

Peer est conçu selon les principes de l'architecture hexagonale (ou architecture en ports et adaptateurs), qui permet une séparation claire entre la logique métier et les détails techniques d'implémentation.

## Couches Architecturales

### 1. Couche Domaine

La couche domaine contient la logique métier centrale de l'application, indépendante de toute technologie spécifique.

#### Entités

Les entités représentent les concepts fondamentaux du domaine :
- `Session` : Représente une session de travail avec l'assistant
- `CodeAnalysisResult` : Résultat d'une analyse de code
- `FeedbackMessage` : Message de feedback généré par l'assistant

#### Ports

Les ports définissent les interfaces que les adaptateurs doivent implémenter :
- `LLMPort` : Interface pour les modèles de langage
- `TTSPort` : Interface pour la synthèse vocale
- `CodeAnalysisPort` : Interface pour l'analyse de code
- `PluginPort` : Interface pour les plugins

#### Services

Les services implémentent la logique métier :
- `PeerAssistantService` : Service principal de l'assistant
- `SessionService` : Gestion des sessions de travail
- `AnalysisService` : Coordination des analyses de code

### 2. Couche Application

La couche application orchestre les cas d'utilisation en coordonnant les entités et services du domaine.

#### Services d'Application

- `ApplicationService` : Coordonne les différents services du domaine
- `PluginManager` : Gère le chargement et l'exécution des plugins
- `ConfigurationService` : Gère la configuration de l'application

#### Événements

- `EventBus` : Système de communication par événements entre les composants
- `EventHandlers` : Gestionnaires d'événements spécifiques

### 3. Couche Infrastructure

La couche infrastructure contient les implémentations concrètes des ports définis dans le domaine.

#### Adaptateurs

- **LLM** : Adaptateurs pour les modèles de langage (Devstral, Qwen3, Deepseek, Claude 4)
- **TTS** : Adaptateurs pour la synthèse vocale (Piper, pyttsx3)
- **Code Analysis** : Adaptateurs pour l'analyse de code (Tree-sitter, Ruff)
- **IDE** : Adaptateurs pour l'intégration avec les IDE (VSCode, etc.)
- **VCS** : Adaptateurs pour l'intégration avec les systèmes de contrôle de version (Git, etc.)

#### Services d'Infrastructure

- `LoggingService` : Service de journalisation
- `StorageService` : Service de stockage persistant

### 4. Interfaces

Les interfaces exposent les fonctionnalités de l'application aux utilisateurs.

- **CLI** : Interface en ligne de commande
- **TUI** : Interface textuelle interactive
- **API** : Interface REST pour l'intégration avec d'autres outils

## Flux de Données

1. L'utilisateur interagit avec une des interfaces (CLI, TUI, API)
2. L'interface transmet la demande à la couche application
3. La couche application coordonne les services du domaine
4. Les services du domaine utilisent les ports pour interagir avec l'infrastructure
5. Les adaptateurs de l'infrastructure communiquent avec les systèmes externes
6. Les résultats remontent à travers les couches jusqu'à l'interface utilisateur

## Système de Plugins

Le système de plugins permet d'étendre les fonctionnalités de Peer sans modifier le code principal :

1. Les plugins implémentent l'interface `PluginPort` du domaine
2. Le `PluginManager` de la couche application découvre et charge les plugins
3. Les plugins peuvent fournir des fonctionnalités spécifiques (analyse, génération, etc.)
4. Les plugins peuvent utiliser les services du domaine via des interfaces dédiées

## Principes de Conception

- **Inversion de dépendance** : Les couches internes ne dépendent pas des couches externes
- **Séparation des préoccupations** : Chaque composant a une responsabilité unique
- **Testabilité** : L'architecture facilite les tests unitaires et d'intégration
- **Extensibilité** : Nouvelles fonctionnalités ajoutables sans modifier le code existant
- **Indépendance technologique** : Les technologies externes peuvent être remplacées sans affecter la logique métier
