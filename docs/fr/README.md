# Documentation de la Phase 5 du Projet Peer

## Introduction

Ce document présente la phase 5 du développement de Peer, un assistant de développement omniscient avec feedback vocal. Cette phase se concentre sur l'implémentation des adaptateurs LLM, TTS et d'analyse de code, ainsi que sur le système de plugins et les intégrations IDE/VCS.

## Structure du Projet

La structure du projet a été réorganisée selon l'architecture hexagonale, avec une séparation claire entre le domaine, l'application, l'infrastructure et les interfaces :

```
peer_phase5_restructured/
├── docs/
│   └── fr/
│       ├── architecture/
│       ├── conception/
│       └── plan/
├── src/
│   └── peer/
│       ├── domain/
│       │   ├── entities/
│       │   ├── ports/
│       │   └── services/
│       ├── application/
│       │   ├── config/
│       │   ├── event/
│       │   ├── plugins/
│       │   └── services/
│       ├── infrastructure/
│       │   ├── adapters/
│       │   │   ├── code_analysis/
│       │   │   ├── ide/
│       │   │   ├── llm/
│       │   │   ├── persistence/
│       │   │   ├── tts/
│       │   │   └── vcs/
│       │   └── services/
│       └── interfaces/
│           ├── api/
│           ├── cli/
│           └── tui/
├── tests/
│   ├── integration/
│   └── unit/
│       ├── application/
│       ├── domain/
│       ├── infrastructure/
│       └── interfaces/
└── plugins/
    ├── architect/
    ├── developer/
    ├── reviewer/
    └── tester/
```

## Adaptateurs Implémentés

### Adaptateurs LLM

Les adaptateurs LLM suivants ont été implémentés :

- **DevstralAdapter** : Adaptateur pour le modèle Devstral via Ollama
- **Qwen3Adapter** : Adaptateur pour le modèle Qwen3 via Ollama
- **DeepseekCoderAdapter** : Adaptateur pour le modèle Deepseek-Coder via Ollama
- **AnthropicAdapter** : Adaptateur pour Claude 4 via l'API Anthropic

### Adaptateurs TTS

Les adaptateurs TTS suivants ont été implémentés :

- **PiperAdapter** : Adaptateur pour Piper, supportant des voix françaises et anglaises
- **PyttsxAdapter** : Adaptateur pour pyttsx3, offrant une solution de repli

### Adaptateurs d'Analyse de Code

Les adaptateurs d'analyse de code suivants ont été implémentés :

- **TreeSitterAdapter** : Analyse syntaxique pour Python, TypeScript/JavaScript, Shell, Markdown, HTML et CSS
- **RuffAdapter** : Analyse statique pour Python

## Interfaces Utilisateur

Trois interfaces utilisateur ont été implémentées :

- **CLI** : Interface en ligne de commande pour une utilisation rapide et scriptable
- **TUI** : Interface textuelle pour une utilisation interactive
- **API** : Interface REST pour l'intégration avec d'autres outils

## Système de Plugins

Un système de plugins extensible a été implémenté, permettant d'ajouter facilement de nouvelles fonctionnalités à Peer. Les plugins suivants sont disponibles :

- **Developer** : Assistance au développement
- **Architect** : Assistance à l'architecture
- **Reviewer** : Assistance à la revue de code
- **Tester** : Assistance aux tests

## Tests

Une suite de tests complète a été mise en place :

- **Tests unitaires** : Pour chaque composant individuel
- **Tests d'intégration** : Pour vérifier l'interaction entre les composants

## Installation et Utilisation

### Prérequis

- Python 3.10+
- Ollama (pour les modèles LLM locaux)
- Piper (pour la synthèse vocale)

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/example/peer.git
cd peer

# Installer les dépendances
./install.sh
```

### Utilisation

```bash
# Interface CLI
./run.sh cli

# Interface TUI
./run.sh tui

# Interface API
./run.sh api
```

## Prochaines Étapes

La phase 6 se concentrera sur :

1. L'amélioration des performances des adaptateurs
2. L'extension du système de plugins
3. L'intégration avec davantage d'IDE et de systèmes VCS
4. L'amélioration de l'interface utilisateur
5. L'ajout de fonctionnalités d'analyse continue et de feedback en temps réel
