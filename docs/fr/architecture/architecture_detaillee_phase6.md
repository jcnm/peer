# Documentation d'Architecture - Peer Assistant Omniscient (Phase 6)

## Introduction

Ce document présente l'architecture détaillée du Peer Assistant Omniscient développé dans la phase 6, avec un focus particulier sur l'intégration de l'interface vocale bidirectionnelle (SUI - Speech User Interface) et l'orchestration événementielle des différents services.

## Architecture Hexagonale

Le projet Peer est structuré selon une architecture hexagonale (ou architecture en ports et adaptateurs) qui offre plusieurs avantages :

1. **Séparation des préoccupations** : Le domaine métier est isolé des détails techniques d'implémentation
2. **Testabilité accrue** : Les composants peuvent être testés indépendamment grâce aux interfaces bien définies
3. **Flexibilité d'implémentation** : Les adaptateurs peuvent être remplacés sans modifier le domaine
4. **Évolutivité** : Facilite l'ajout de nouvelles fonctionnalités ou interfaces

### Structure du Projet

```
/
├── src/
│   ├── peer/
│   │   ├── application/
│   │   │   └── daemon/           # Le coeur de l'application lancé une fois par l'une des interfaces.
│   │   ├── config/               # Peer run configuration 
│   │   │   └── peer.yml 
│   │   ├── domain/
│   │   │   ├── entities/           # Entités du domaine
│   │   │   │   ├── base_entities.py
│   │   │   │   ├── feedback_entities.py
│   │   │   │   ├── session_entities.py
│   │   │   │   └── speech_entities.py
│   │   │   ├── ports/              # Interfaces (ports)
│   │   │   │   ├── output_ports.py
│   │   │   │   ├── ide_ports.py
│   │   │   │   ├── context_analyzer_ports.py
│   │   │   │   ├── mode_detector_ports.py
│   │   │   │   ├── speech_ports.py
│   │   │   │   └── tts_ports.py
│   │   │   └── services/           # Services du domaine
│   │   │       ├── peer_assistant_service.py
│   │   │       ├── peer_assistant_orchestrator.py
│   │   │       └── vocal_feedback_service.py
│   │   ├── infrastructure/
│   │   │   └── adapters/           # Adaptateurs
│   │   │       ├── llm/
│   │   │       ├── tts/
│   │   │       ├── code_analysis/
│   │   │       ├── ide/
│   │   │       ├── vcs/
│   │   │       ├── context_analyzer/
│   │   │       ├── mode_detector/
│   │   │       └── speech/
│   │   └── interfaces/
│   │       ├── cli/                # Interface en ligne de commande
│   │       │   ├── cli.py
│   │       ├── tui/                # Interface en ligne de commande mais manipulation textuelle 
│   │       │   ├── cli.py
│   │       ├── api/                # Interface en par api
│   │       │   └── api.py
│   │       ├── sui/                # Interface en ligne mais manipulaton audio
│   │       │   └── sui.py
│   │       └── api/                # Interface API
│   └── plugins/                    # Plugins from the community and me to enhance Peer with abilities
├── tests/
│   ├── unit/
│   └── integration/
├── config/             # launching options systheme integration and configurations
├── install.sh
├── diagnose.sh
├── pyproject.toml
├── run.sh              # Run the default cli interfaces: 
├── run_api.sh          # Following will evolve to sub-options: peer [api|sui|tui|cli (by default)] [option]
├── run_tui.sh
├── run_sui.sh
└── run_tests.sh
```

## Composants Principaux

### 1. Adaptateurs IDE (VSCode/PyCharm)

Les adaptateurs IDE permettent à Peer de recevoir des événements des éditeurs de code et d'interagir avec eux.

**Choix technologiques :**
- Utilisation des API VSCode et PyCharm pour la communication bidirectionnelle
- Implémentation d'un système d'événements pour capturer les modifications, sélections, etc.
- Abstraction via l'interface `IDEPort` pour garantir l'indépendance du domaine

**Validation :**
- Les adaptateurs IDE sont capables de recevoir les événements en temps réel
- L'interface est suffisamment abstraite pour supporter différents éditeurs
- Les tests unitaires confirment le bon fonctionnement des adaptateurs

### 2. Analyseur de Contexte

L'analyseur de contexte examine le contexte de développement (fichier ouvert, fonction, projet) pour fournir des informations structurées au Peer Assistant.

**Choix technologiques :**
- Tree-sitter pour l'analyse syntaxique précise du code
- Intégration avec des LLM (via Ollama) pour l'analyse sémantique avancée
- Système de cache pour optimiser les performances

**Validation :**
- L'analyseur Tree-sitter fournit une analyse syntaxique précise et performante
- L'intégration LLM permet une compréhension plus profonde du contexte
- Les tests confirment la capacité à extraire des informations pertinentes du code

### 3. Service de Détection de Mode

Ce service détermine le mode le plus approprié selon le contexte de développement.

**Choix technologiques :**
- Système de règles configurable pour la détection basée sur des heuristiques
- Intégration optionnelle avec des LLM pour une détection plus intelligente
- Architecture extensible permettant d'ajouter facilement de nouveaux modes

**Validation :**
- Le détecteur de mode identifie correctement les contextes d'édition, de débogage, etc.
- Le système de règles est suffisamment flexible pour s'adapter à différents workflows
- Les tests confirment la précision de la détection dans divers scénarios

### 4. Interface Vocale Bidirectionnelle (SUI)

L'interface SUI permet d'envoyer des commandes orales et de recevoir des retours oraux.

**Choix technologiques :**
- **Piper 1.3.0** pour la synthèse vocale (TTS) locale de haute qualité
- **SpeechRecognition 3.10.0** pour la reconnaissance vocale (STT)
- Système d'écoute continue, même pendant que Peer parle
- Architecture multi-thread pour garantir la réactivité

**Validation :**
- Piper offre une qualité vocale supérieure aux alternatives locales
- SpeechRecognition fournit une reconnaissance précise et multilingue
- L'écoute continue permet d'interrompre Peer ou d'ajuster le volume à la volée
- Les tests confirment la robustesse de l'interface vocale bidirectionnelle

### 5. Orchestrateur du Peer Assistant

L'orchestrateur coordonne tous les services pour fournir une assistance intelligente et contextuelle.

**Choix technologiques :**
- Architecture événementielle basée sur `asyncio` pour la gestion asynchrone
- Système de file d'attente pour le traitement ordonné des événements
- Gestion des callbacks pour la communication entre les composants
- Support des modes synchrone et asynchrone pour maximiser la compatibilité

**Validation :**
- L'orchestrateur gère efficacement les événements de tous les services
- Le système asynchrone garantit la réactivité de l'interface utilisateur
- Les tests d'intégration confirment la coordination correcte entre tous les composants

## Intégration Événementielle

L'architecture événementielle est au cœur du Peer Assistant Omniscient, permettant une coordination fluide entre tous les services.

### Flux d'Événements

1. **Capture d'événements** : Les adaptateurs IDE et l'interface vocale capturent les événements utilisateur
2. **Mise en file d'attente** : Les événements sont placés dans une file d'attente pour traitement ordonné
3. **Traitement asynchrone** : Les événements sont traités de manière asynchrone pour maintenir la réactivité
4. **Analyse du contexte** : Le contexte est analysé en fonction des événements reçus
5. **Détection de mode** : Le mode le plus approprié est déterminé selon le contexte
6. **Réponse adaptative** : Peer répond de manière adaptée au contexte et au mode détecté

### Gestion des Interruptions

Un aspect clé de l'interface SUI est la capacité à gérer les interruptions vocales :

- Peer continue à écouter même pendant qu'il parle
- Les commandes vocales comme "stop" ou "plus bas" sont traitées immédiatement
- Le système de priorité garantit que les commandes critiques sont exécutées en premier

## Validation Technologique

### Synthèse Vocale (TTS)

**Piper 1.3.0** a été sélectionné après comparaison avec d'autres solutions :

| Solution | Qualité | Performance | Taille | Personnalisation | Note |
|----------|---------|-------------|--------|-----------------|------|
| Piper 1.3.0 | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★★★ | Solution retenue |
| pyttsx3 | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★☆☆☆ | Alternative légère |
| gTTS | ★★★★☆ | ★★☆☆☆ | ★★★★★ | ★★☆☆☆ | Nécessite internet |
| espeak | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★☆☆ | Qualité insuffisante |

### Reconnaissance Vocale (STT)

**SpeechRecognition 3.10.0** a été sélectionné pour sa flexibilité et sa précision :

| Solution | Précision | Performance | Hors-ligne | Multilangue | Note |
|----------|-----------|-------------|------------|-------------|------|
| SpeechRecognition 3.10.0 | ★★★★☆ | ★★★☆☆ | ★★★★☆ | ★★★★★ | Solution retenue |
| Whisper | ★★★★★ | ★★☆☆☆ | ★★★★★ | ★★★★★ | Alternative haute précision |
| Vosk | ★★★☆☆ | ★★★★☆ | ★★★★★ | ★★★★☆ | Alternative légère |
| DeepSpeech | ★★★★☆ | ★★☆☆☆ | ★★★★★ | ★★★☆☆ | Ressources importantes |

### Analyse de Code

**Tree-sitter** a été sélectionné pour l'analyse syntaxique précise :

| Solution | Précision | Performance | Multi-langage | Intégration | Note |
|----------|-----------|-------------|--------------|-------------|------|
| Tree-sitter | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ | Solution retenue |
| libCST | ★★★★☆ | ★★★☆☆ | ★★☆☆☆ | ★★★★☆ | Alternative pour Python |
| Pygments | ★★★☆☆ | ★★★★☆ | ★★★★★ | ★★★★★ | Pour coloration syntaxique |
| AST module | ★★★★☆ | ★★★★★ | ★☆☆☆☆ | ★★★★★ | Limité à Python |

## Performances et Optimisations

Plusieurs optimisations ont été mises en place pour garantir les performances du Peer Assistant :

1. **Analyse contextuelle incrémentale** : Seules les parties modifiées du code sont réanalysées
2. **Mise en cache des résultats d'analyse** : Évite les analyses redondantes
3. **Traitement asynchrone** : Garantit la réactivité de l'interface utilisateur
4. **Détection intelligente des changements significatifs** : Évite les analyses inutiles
5. **Prioritisation des événements** : Les événements critiques sont traités en premier

## Extensibilité

L'architecture a été conçue pour faciliter l'extension future :

1. **Nouveaux adaptateurs IDE** : Support facile de nouveaux éditeurs
2. **Nouveaux modes d'assistance** : Ajout simple de nouveaux modes spécialisés
3. **Nouvelles voix et langues** : Extension facile des capacités vocales
4. **Nouveaux LLM** : Intégration simple de nouveaux modèles de langage
5. **Nouvelles interfaces utilisateur** : Ajout possible d'interfaces graphiques, etc.

## Conclusion

L'architecture du Peer Assistant Omniscient (Phase 6) offre une base solide pour un assistant de développement intelligent, contextuel et vocal. L'approche hexagonale garantit la maintenabilité et l'évolutivité, tandis que l'orchestration événementielle assure une expérience utilisateur fluide et réactive.

Les validations technologiques confirment la pertinence des choix effectués, notamment Piper pour la synthèse vocale, SpeechRecognition pour la reconnaissance vocale, Tree-sitter pour l'analyse de code, et asyncio pour l'orchestration événementielle.

Cette architecture pose les fondations pour les évolutions futures du Peer Assistant, notamment l'intégration de nouvelles capacités d'analyse, de nouveaux modes d'assistance, et de nouvelles interfaces utilisateur.
