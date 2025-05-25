# Architecture et Intégration de l'Interface SUI (Speech User Interface)

## Introduction

Ce document détaille l'architecture et l'intégration de l'interface vocale (SUI) dans le projet Peer. L'interface SUI permet une interaction bidirectionnelle par la voix avec l'assistant Peer, offrant une expérience utilisateur plus naturelle et immersive.

## Principes fondamentaux

### Écoute continue pendant la restitution vocale

Une caractéristique essentielle de l'interface SUI est sa capacité à **écouter en continu, même pendant que Peer parle**. Cela permet à l'utilisateur de :
- Interrompre Peer pendant qu'il parle
- Demander à Peer de parler moins fort ou plus fort
- Poser des questions complémentaires sans attendre la fin d'une explication
- Rediriger la conversation de manière fluide et naturelle

Cette fonctionnalité est implémentée via un système de threads parallèles pour la reconnaissance vocale et la synthèse vocale, avec un mécanisme de priorité pour les interruptions.

### Architecture modulaire et extensible

L'interface SUI est conçue selon les principes de l'architecture hexagonale, avec :
- Des ports clairement définis dans le domaine
- Des adaptateurs d'infrastructure interchangeables
- Une intégration non-intrusive avec le service Peer Assistant existant

Cette approche permet d'ajouter ou de remplacer facilement des composants (moteurs de reconnaissance vocale, synthèse vocale, etc.) sans modifier le cœur du système.

## Architecture détaillée

### 1. Ports du domaine

Deux nouveaux ports ont été définis dans le domaine :

#### SpeechRecognitionPort
Interface pour les adaptateurs de reconnaissance vocale :
- `recognize_speech` : Convertit un signal audio en texte
- `get_available_languages` : Liste les langues disponibles
- `start_continuous_recognition` : Démarre la reconnaissance continue
- `stop_continuous_recognition` : Arrête la reconnaissance continue

#### CommandRecognizerPort
Interface pour les adaptateurs de reconnaissance de commandes :
- `extract_command` : Extrait une commande à partir d'un texte
- `get_available_commands` : Liste les commandes disponibles
- `register_command_pattern` : Enregistre un nouveau pattern de commande

### 2. Entités du domaine

Nouvelles entités pour représenter les concepts liés à l'interface vocale :

#### Entités de reconnaissance vocale
- `SpeechRecognitionRequest` : Requête de reconnaissance vocale
- `SpeechRecognitionResponse` : Réponse de reconnaissance vocale
- `SpeechRecognitionStatus` : Statut de la reconnaissance (succès, erreur, etc.)

#### Entités de commande
- `Command` : Représentation d'une commande vocale
- `CommandParameter` : Paramètre d'une commande
- `CommandType` : Types de commandes (navigation, édition, analyse, etc.)
- `CommandContext` : Contexte d'exécution d'une commande
- `CommandRecognitionRequest` : Requête de reconnaissance de commande
- `CommandRecognitionResponse` : Réponse de reconnaissance de commande

#### Entités de feedback
- `SpeechFeedback` : Feedback vocal à transmettre à l'utilisateur

### 3. Services du domaine

#### SUIService
Service central qui coordonne la reconnaissance vocale, l'interprétation des commandes et le feedback vocal :
- Gère le cycle de vie de la reconnaissance vocale
- Interprète les commandes vocales
- Achemine les commandes vers le service Peer Assistant
- Fournit un feedback vocal à l'utilisateur

#### PeerAssistantWithSUI
Extension du service Peer Assistant qui intègre l'interface vocale :
- Hérite de PeerAssistantService
- Ajoute la gestion de l'interface vocale
- Coordonne les interactions entre le service Peer Assistant et l'interface SUI
- Maintient la cohérence du contexte entre les deux services

### 4. Adaptateurs d'infrastructure

#### Adaptateurs de reconnaissance vocale
- `BaseSpeechRecognitionAdapter` : Classe de base pour tous les adaptateurs
- `WhisperAdapter` : Adaptateur pour le modèle Whisper
- `WebSpeechAdapter` : Adaptateur pour l'API Web Speech
- `MockSpeechRecognitionAdapter` : Adaptateur de simulation pour les tests

#### Adaptateurs de reconnaissance de commandes
- `BaseCommandRecognizerAdapter` : Classe de base pour tous les adaptateurs
- `NLPCommandRecognizerAdapter` : Adaptateur basé sur le traitement du langage naturel
- `MockCommandRecognizerAdapter` : Adaptateur de simulation pour les tests

### 5. Interface utilisateur

#### CLI avec support SUI
- `PeerCLIWithSUI` : Extension de l'interface CLI standard avec support SUI
- Ajoute des options pour activer/configurer l'interface vocale
- Intègre le service Peer Assistant avec SUI

## Flux d'interaction

### 1. Reconnaissance vocale continue

1. L'utilisateur démarre Peer avec l'option `--voice`
2. Le service SUI initialise les adaptateurs de reconnaissance vocale et de commandes
3. La reconnaissance vocale continue est démarrée en arrière-plan
4. L'utilisateur peut parler à tout moment, même pendant que Peer parle
5. Le texte reconnu est transmis à l'adaptateur de reconnaissance de commandes

### 2. Interprétation des commandes

1. L'adaptateur de reconnaissance de commandes analyse le texte
2. Si une commande est reconnue, elle est extraite avec ses paramètres
3. La commande est transmise au service SUI
4. Le service SUI notifie ses callbacks et achemine la commande vers le service approprié

### 3. Exécution des commandes

1. Le service SUI détermine le type de commande (navigation, édition, analyse, etc.)
2. La commande est transmise au service Peer Assistant
3. Le service Peer Assistant exécute la commande
4. Le résultat est renvoyé au service SUI

### 4. Feedback vocal

1. Le service SUI génère un feedback vocal basé sur le résultat de la commande
2. Le feedback est transmis à l'adaptateur TTS
3. L'adaptateur TTS synthétise le feedback en audio
4. L'audio est joué à l'utilisateur
5. **Pendant la lecture audio, la reconnaissance vocale reste active**
6. Si l'utilisateur parle pendant la lecture, sa commande est traitée immédiatement
7. Si la nouvelle commande est une interruption, la lecture en cours est arrêtée

## Gestion des interruptions

L'interface SUI implémente un mécanisme sophistiqué de gestion des interruptions :

1. Détection des commandes d'interruption ("arrête", "stop", "tais-toi", etc.)
2. Priorité des commandes d'interruption sur les autres commandes
3. Arrêt immédiat de la synthèse vocale en cours
4. Confirmation vocale brève de l'interruption
5. Attente de la prochaine commande

Ce mécanisme permet une interaction naturelle et fluide, similaire à une conversation humaine.

## Intégration avec les composants existants

### Intégration avec PeerAssistantService

L'intégration avec le service Peer Assistant existant est réalisée via l'extension `PeerAssistantWithSUI`, qui :
- Hérite de toutes les fonctionnalités du service standard
- Ajoute la gestion de l'interface vocale
- Maintient la compatibilité avec les interfaces existantes
- Enrichit le contexte avec les informations vocales

### Intégration avec les adaptateurs TTS

L'interface SUI réutilise les adaptateurs TTS existants pour la synthèse vocale, en ajoutant :
- La gestion des interruptions
- Le contrôle du volume et de la vitesse
- La synchronisation entre reconnaissance et synthèse

### Intégration avec l'interface CLI

L'interface CLI est étendue pour supporter l'interface vocale via `PeerCLIWithSUI`, qui :
- Ajoute des options spécifiques à SUI
- Initialise les adaptateurs nécessaires
- Gère le cycle de vie de l'interface vocale

## Tests et validation

### Tests unitaires

Des tests unitaires complets ont été développés pour :
- Les adaptateurs de reconnaissance vocale
- Les adaptateurs de reconnaissance de commandes
- Le service SUI
- L'intégration avec le service Peer Assistant

### Tests d'intégration

Des tests d'intégration valident :
- Le flux complet de reconnaissance vocale → exécution de commande → feedback vocal
- La gestion des interruptions
- La compatibilité avec les interfaces existantes

## Fichiers essentiels à la racine du projet

Pour faciliter l'utilisation et la configuration de Peer, les fichiers suivants sont inclus à la racine du projet :

### Scripts de lancement et d'installation
- **run.sh** : Script principal pour exécuter Peer
- **run_tests.sh** : Script pour exécuter les tests unitaires
- **install.sh** : Script d'installation des dépendances

### Configuration et documentation
- **pyproject.toml** : Configuration du projet et des dépendances
- **README.md** : Documentation principale du projet
- **QUICKSTART.md** : Guide de démarrage rapide
- **TODO.md** : Liste des tâches à accomplir

Ces fichiers sont essentiels pour la mise en place, la configuration et le suivi des activités de Peer.

## Limitations connues et évolutions futures

### Limitations actuelles
- Sensibilité au bruit ambiant pour la reconnaissance vocale
- Vocabulaire technique limité pour certains moteurs de reconnaissance
- Latence potentielle pour les commandes complexes

### Évolutions prévues
- Support de langues supplémentaires
- Amélioration de la reconnaissance de vocabulaire technique
- Personnalisation avancée des voix et des commandes
- Intégration avec des assistants vocaux externes

## Conclusion

L'interface SUI représente une avancée majeure pour le projet Peer, offrant une interaction naturelle et immersive avec l'assistant. Sa conception modulaire et son intégration non-intrusive avec les composants existants garantissent sa robustesse et son extensibilité.

La capacité d'écoute continue pendant la restitution vocale, permettant les interruptions et les ajustements à la volée, constitue une fonctionnalité clé qui rapproche Peer d'une véritable conversation humaine.
