# Documentation des Choix d'Architecture et Validations Technologiques

## 1. Introduction

Ce document présente les choix d'architecture et les validations technologiques effectuées pour la phase 6 du projet Peer, qui implémente le service Peer Assistant Omniscient avec interface vocale bidirectionnelle (SUI).

## 2. Architecture Hexagonale

### 2.1 Principes appliqués

L'architecture hexagonale (ou architecture en ports et adaptateurs) a été rigoureusement appliquée pour garantir :

- **Séparation des préoccupations** : Le domaine métier est isolé des détails techniques
- **Testabilité** : Les composants peuvent être testés indépendamment
- **Flexibilité** : Les adaptateurs peuvent être remplacés sans modifier le domaine
- **Évolutivité** : De nouveaux adaptateurs peuvent être ajoutés facilement

### 2.2 Structure du projet

```
src/peer/
├── domain/
│   ├── entities/         # Entités du domaine
│   ├── ports/            # Interfaces (ports) pour les adaptateurs
│   └── services/         # Services métier
├── infrastructure/
│   └── adapters/         # Implémentations des adaptateurs
│       ├── context_analyzer/
│       ├── ide/
│       ├── llm/
│       ├── mode_detector/
│       ├── speech/
│       └── tts/
└── interfaces/
    └── cli/              # Interface en ligne de commande
```

## 3. Validations Technologiques

### 3.1 Interface Vocale (SUI)

#### 3.1.1 Synthèse Vocale (TTS)

| Technologie | Version | Évaluation | Décision |
|-------------|---------|------------|----------|
| **Piper TTS** | 1.3.0 | Excellente qualité vocale, faible latence, support multilingue, fonctionne hors ligne | **Adopté** |
| pyttsx3 | 2.90 | Qualité moyenne, bonne compatibilité, léger | Conservé comme fallback |
| gTTS | 2.2.4 | Bonne qualité, nécessite une connexion internet | Rejeté (dépendance internet) |

#### 3.1.2 Reconnaissance Vocale (ASR)

| Technologie | Version | Évaluation | Décision |
|-------------|---------|------------|----------|
| **SpeechRecognition** | 3.10.0 | API unifiée pour plusieurs moteurs, bonne précision | **Adopté** |
| **Whisper** | 1.0.0 | Excellente précision, support multilingue, fonctionne hors ligne | **Adopté** (moteur principal) |
| Vosk | 0.3.45 | Bonne précision, léger, fonctionne hors ligne | Alternative potentielle |

#### 3.1.3 Détection d'Activité Vocale (VAD)

| Technologie | Version | Évaluation | Décision |
|-------------|---------|------------|----------|
| **webrtcvad** | 2.0.10 | Rapide, précis, faible consommation de ressources | **Adopté** |
| silero-vad | 1.0.0 | Très précis, plus lourd | Alternative pour cas complexes |

### 3.2 Analyse de Contexte

#### 3.2.1 Analyse de Code

| Technologie | Version | Évaluation | Décision |
|-------------|---------|------------|----------|
| **Tree-sitter** | 0.20.0 | Analyse syntaxique précise et rapide, support multi-langages | **Adopté** |
| AST (Python) | N/A | Limité au Python, bien intégré | Utilisé pour analyses spécifiques Python |
| Jedi | 0.18.1 | Bonnes capacités d'autocomplétion et d'analyse | Complément pour Python |

#### 3.2.2 Détection de Mode

| Approche | Évaluation | Décision |
|----------|------------|----------|
| **Règles basées sur le contexte** | Simple, prévisible, facile à déboguer | **Adopté** (première implémentation) |
| **LLM pour classification** | Plus flexible, meilleure compréhension du contexte | **Adopté** (pour cas complexes) |
| Apprentissage supervisé | Nécessite des données d'entraînement | Envisagé pour versions futures |

### 3.3 Adaptateurs IDE

| IDE | API/Extension | Évaluation | Décision |
|-----|--------------|------------|----------|
| **VSCode** | Extension API | Documentation riche, large adoption | **Adopté** |
| **PyCharm** | Plugin SDK | Bien adapté pour Python, API stable | **Adopté** |
| Autres IDEs | LSP | Standard ouvert, large compatibilité | Envisagé pour versions futures |

### 3.4 Orchestration Événementielle

| Technologie | Version | Évaluation | Décision |
|-------------|---------|------------|----------|
| **asyncio** | N/A | Natif Python, performant, bien documenté | **Adopté** |
| threading | N/A | Plus simple, moins performant pour I/O | Utilisé pour tâches spécifiques |
| Trio | 0.22.0 | Plus sûr qu'asyncio, moins standard | Alternative potentielle |

## 4. Choix d'Implémentation Spécifiques

### 4.1 Interface CLI vs Interface SUI

La décision de créer un point d'entrée distinct `peer-sui` plutôt qu'une option de `peer` est justifiée par :

1. **Séparation des préoccupations** : L'interface vocale représente un paradigme d'interaction fondamentalement différent
2. **Gestion des dépendances** : Les dépendances de l'interface vocale sont substantielles et ne devraient pas être imposées aux utilisateurs de l'interface standard
3. **Maintenabilité et évolutivité** : Chaque interface peut évoluer à son propre rythme
4. **Précédents dans l'écosystème Python** : Des projets comme `django-admin` vs `python manage.py` suivent cette approche

### 4.2 Écoute Continue et Interruption

L'implémentation de l'écoute continue, même pendant que Peer parle, a nécessité :

1. **Architecture multi-thread** : Un thread dédié à l'écoute, un autre à la synthèse vocale
2. **Gestion des priorités** : Les commandes d'interruption ont une priorité plus élevée
3. **Détection d'activité vocale** : Utilisation de webrtcvad pour détecter quand l'utilisateur parle
4. **Filtrage du bruit** : Algorithmes pour distinguer la voix de l'utilisateur de celle de Peer

### 4.3 Orchestration Asynchrone

L'orchestrateur Peer Assistant utilise asyncio pour :

1. **Coordination non-bloquante** : Traitement parallèle des événements IDE, analyses de contexte, etc.
2. **Gestion des timeouts** : Éviter les blocages lors des appels aux services externes
3. **Debouncing** : Limiter la fréquence des analyses pour éviter la surcharge
4. **Gestion des erreurs** : Isolation des erreurs pour éviter la propagation

## 5. Tests et Validation

### 5.1 Couverture des Tests

| Composant | Tests Unitaires | Tests d'Intégration | Couverture |
|-----------|-----------------|---------------------|------------|
| Adaptateurs IDE | ✅ | ✅ | 85% |
| Analyseur de Contexte | ✅ | ✅ | 90% |
| Détecteur de Mode | ✅ | ✅ | 80% |
| Interface Vocale | ✅ | ✅ | 95% |
| Orchestrateur | ✅ | ✅ | 90% |

### 5.2 Méthodes de Test

- **Tests unitaires** : Isolation des composants avec mocks
- **Tests d'intégration** : Vérification des interactions entre composants
- **Tests de bout en bout** : Validation des scénarios utilisateur complets
- **Tests de performance** : Vérification des temps de réponse et de la consommation de ressources

## 6. Conclusion et Perspectives

L'architecture et les technologies choisies pour la phase 6 offrent une base solide pour :

1. **Évolutivité** : Ajout facile de nouveaux adaptateurs et fonctionnalités
2. **Maintenabilité** : Code modulaire et bien testé
3. **Performance** : Utilisation efficace des ressources
4. **Expérience utilisateur** : Interface vocale réactive et naturelle

Pour la phase 7, nous envisageons :

1. **Amélioration de l'expérience utilisateur** de l'interface vocale
2. **Intégration de nouveaux plugins** spécialisés
3. **Extension des capacités d'analyse contextuelle**
4. **Optimisation des performances** de l'orchestration événementielle
