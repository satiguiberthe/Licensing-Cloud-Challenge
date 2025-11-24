# Choix Techniques et Options Écartées

## Vue d'ensemble

Ce document présente les choix techniques effectués lors du développement du système de gestion de licences cloud, ainsi que les alternatives qui ont été écartées et les raisons de ces décisions.

---

## 1. Architecture Générale

### ✅ Choix : Architecture Monolithique Modulaire

**Décision :** Application Django monolithique avec une structure modulaire claire (licenses, applications, jobs, utility).

**Justification :**
- **Simplicité de déploiement** : Un seul conteneur Docker pour le backend
- **Développement rapide** : Pas de complexité liée à la communication inter-services
- **Maintenance facilitée** : Code centralisé, plus facile à déboguer
- **Performance** : Pas de latence réseau entre services
- **Cohérence transactionnelle** : Transactions ACID garanties sur une seule base de données

**Alternatives écartées :**
- **Architecture microservices** : Écartée car :
  - Complexité opérationnelle accrue (orchestration, service discovery, load balancing)
  - Nécessite plusieurs bases de données ou synchronisation complexe
  - Surcharge de communication réseau
  - Non justifiée pour la charge attendue initiale

**Migration future :** L'architecture modulaire permet une migration progressive vers des microservices si nécessaire (par exemple, séparer le service de quotas en service indépendant).

---

## 2. Authentification JWT

### ✅ Choix : Authentification Hybride (User + License)

**Décision :** Implémentation d'une classe `HybridJWTAuthentication` qui supporte à la fois les tokens utilisateur et les tokens de licence.

**Justification :**
- **Flexibilité** : Permet aux utilisateurs de se connecter directement ou via une licence
- **Compatibilité** : Supporte les deux cas d'usage sans duplication de code
- **Sécurité** : Vérification côté serveur de la signature JWT pour les deux types
- **Expérience utilisateur** : Les utilisateurs peuvent accéder au système sans licence préalable (création automatique d'une licence par défaut)

**Alternatives écartées :**
- **Authentification séparée** : Deux systèmes d'authentification distincts
  - Écartée car : Duplication de code, maintenance complexe, confusion pour les développeurs
- **OAuth2 / OpenID Connect** : 
  - Écartée car : Complexité excessive pour les besoins actuels, nécessite un serveur d'autorisation externe
- **Session-based authentication** :
  - Écartée car : Non stateless, nécessite un stockage côté serveur, moins adapté aux APIs REST

**Détails techniques :**
- Algorithme : HS256 (HMAC-SHA256)
- Durée de vie : 24 heures (configurable via `JWT_ACCESS_TOKEN_LIFETIME`)
- Vérification : Signature cryptographique côté serveur uniquement
- Pas de stockage côté client : Tokens stateless

---

## 3. Gestion des Quotas

### ✅ Choix : Redis avec Sorted Sets pour la Fenêtre Glissante

**Décision :** Utilisation de Redis avec des sorted sets (ZSET) pour implémenter la fenêtre glissante de 24 heures pour les exécutions.

**Justification :**
- **Performance** : Opérations O(log N) pour les requêtes de plage temporelle
- **Atomicité** : Opérations atomiques natives de Redis
- **Efficacité mémoire** : Stockage optimisé pour les données temporelles
- **Nettoyage automatique** : Expiration automatique des clés après 24h
- **Scalabilité** : Redis peut gérer des millions d'opérations par seconde

**Alternatives écartées :**
- **PostgreSQL avec requêtes temporelles** :
  - Écartée car : Plus lent (requêtes SQL complexes), surcharge de la base principale, moins efficace pour les opérations temporelles
- **In-memory Python (dictionnaires)** :
  - Écartée car : Non persistant, non partagé entre instances, risque de perte de données
- **Base de données temporelle (TimescaleDB)** :
  - Écartée car : Complexité d'installation, surcharge pour ce cas d'usage simple

**Détails d'implémentation :**
- Clé Redis : `executions:{tenant_id}`
- Score : Timestamp Unix
- Valeur : `{job_id}:{timestamp}`
- Nettoyage : Suppression automatique des exécutions > 24h via `ZREMRANGEBYSCORE`

---

## 4. Prévention des Conditions de Course

### ✅ Choix : Verrous Distribués avec Redis

**Décision :** Utilisation de verrous distribués (Redis locks) pour garantir l'atomicité des opérations de quota.

**Justification :**
- **Atomicité garantie** : Empêche les conditions de course même avec plusieurs instances
- **Simplicité** : Implémentation directe avec `django-redis`
- **Performance** : Verrous à faible latence (Redis in-memory)
- **Timeout** : Limite de 5 secondes pour éviter les blocages

**Alternatives écartées :**
- **Optimistic Locking (versioning)** :
  - Écartée car : Nécessite des retries multiples, complexité de gestion des conflits, moins prévisible
- **Transactions SQL avec SELECT FOR UPDATE** :
  - Écartée car : Ne fonctionne pas avec Redis, nécessite une base de données relationnelle pour les quotas
- **Queue-based processing** :
  - Écartée car : Latence ajoutée, complexité de gestion des files d'attente, surcharge pour des opérations synchrones

**Détails d'implémentation :**
- Clé de verrou : `lock:executions:{tenant_id}`
- Timeout : 5 secondes
- Granularité : Par tenant (pas de contention entre tenants différents)

---

## 5. Frontend : Angular Standalone Components

### ✅ Choix : Angular avec Standalone Components

**Décision :** Utilisation d'Angular 18+ avec des composants standalone (pas de NgModules).

**Justification :**
- **Modernité** : Approche recommandée par Angular depuis la version 14+
- **Simplicité** : Moins de boilerplate, pas besoin de déclarer les modules
- **Tree-shaking** : Meilleure optimisation du bundle
- **Flexibilité** : Import direct des dépendances nécessaires
- **Maintenabilité** : Code plus clair et organisé

**Alternatives écartées :**
- **React** :
  - Écartée car : Le projet spécifiait Angular, écosystème différent
- **Vue.js** :
  - Écartée car : Le projet spécifiait Angular, écosystème différent
- **Angular avec NgModules** :
  - Écartée car : Approche legacy, plus de code boilerplate, moins flexible

**Détails d'implémentation :**
- Composants standalone avec `standalone: true`
- Lazy loading des routes avec `loadComponent`
- Services injectés avec `inject()`
- Signals pour la réactivité (Angular 16+)

---

## 6. Séparation Template/Styles

### ✅ Choix : Fichiers .html et .scss séparés

**Décision :** Séparation des templates et styles dans des fichiers externes plutôt que des templates/styles inline.

**Justification :**
- **Maintenabilité** : Code plus lisible et organisé
- **Réutilisabilité** : Styles partagés plus faciles
- **Outils** : Meilleur support IDE (syntax highlighting, autocomplétion)
- **Performance** : Pas d'impact négatif, compilation identique
- **Bonnes pratiques** : Conforme aux recommandations Angular

**Alternatives écartées :**
- **Templates/styles inline** :
  - Écartée car : Fichiers TypeScript trop volumineux, moins lisible, difficile à maintenir

---

## 7. Gestion d'État Frontend

### ✅ Choix : Services avec Signals (Angular Signals)

**Décision :** Utilisation de services avec des signals pour la gestion d'état réactive.

**Justification :**
- **Réactivité native** : Signals intégrés à Angular, performants
- **Simplicité** : Pas besoin de bibliothèque externe (Redux, NgRx)
- **Performance** : Détection de changements optimisée
- **Type-safe** : Support TypeScript complet

**Alternatives écartées :**
- **NgRx (Redux pour Angular)** :
  - Écartée car : Complexité excessive pour ce projet, courbe d'apprentissage élevée, boilerplate important
- **RxJS Subjects uniquement** :
  - Écartée car : Signals plus modernes, meilleure intégration avec Angular, moins de code

**Détails d'implémentation :**
- Services : `LicenseStoreService`, `ApplicationStoreService`, `JobStoreService`
- Signals : `licenses()`, `loading()`, `error()`
- Computed signals : `totalLicenses()`, `activeLicenses()`

---

## 8. Intercepteur HTTP

### ✅ Choix : Intercepteur pour l'ajout automatique du token

**Décision :** Intercepteur HTTP Angular qui ajoute automatiquement le token JWT aux requêtes.

**Justification :**
- **DRY (Don't Repeat Yourself)** : Pas besoin d'ajouter le token manuellement dans chaque service
- **Centralisation** : Gestion des erreurs 401 centralisée
- **Sécurité** : Exclusion automatique des endpoints d'authentification
- **Maintenabilité** : Un seul endroit pour modifier la logique d'authentification

**Alternatives écartées :**
- **Ajout manuel dans chaque service** :
  - Écartée car : Duplication de code, risque d'oubli, maintenance difficile

**Détails d'implémentation :**
- Exclusion des endpoints `/login/` et `/register/`
- Récupération du token depuis `localStorage`
- Gestion automatique de la déconnexion en cas d'erreur 401

---

## 9. Base de Données

### ✅ Choix : PostgreSQL

**Décision :** Utilisation de PostgreSQL comme base de données principale.

**Justification :**
- **ACID** : Garanties transactionnelles complètes
- **Fiabilité** : Base de données mature et éprouvée
- **Performance** : Excellentes performances pour les requêtes complexes
- **Écosystème** : Support Django excellent (ORM natif)
- **Scalabilité** : Supporte de grandes quantités de données

**Alternatives écartées :**
- **MySQL/MariaDB** :
  - Écartée car : PostgreSQL offre de meilleures fonctionnalités (JSON, arrays, full-text search)
- **SQLite** :
  - Écartée car : Non adapté à la production, pas de concurrence réelle
- **MongoDB (NoSQL)** :
  - Écartée car : Pas de garanties ACID complètes, ORM Django moins adapté

---

## 10. Cache et Sessions

### ✅ Choix : Redis pour le cache et les quotas

**Décision :** Utilisation de Redis pour le cache Django et la gestion des quotas.

**Justification :**
- **Performance** : In-memory, très rapide
- **Polyvalence** : Supporte cache, sorted sets, locks
- **Scalabilité** : Peut être clusterisé si nécessaire
- **Persistence** : Options RDB et AOF disponibles

**Alternatives écartées :**
- **Memcached** :
  - Écartée car : Ne supporte pas les sorted sets nécessaires pour les quotas
- **Cache Django en mémoire** :
  - Écartée car : Non partagé entre instances, perdu au redémarrage

---

## 11. Déploiement

### ✅ Choix : Docker Compose

**Décision :** Utilisation de Docker Compose pour orchestrer tous les services.

**Justification :**
- **Simplicité** : Un seul fichier de configuration
- **Reproductibilité** : Environnement identique en développement et production
- **Isolation** : Chaque service dans son propre conteneur
- **Health checks** : Vérification automatique de l'état des services

**Alternatives écartées :**
- **Kubernetes** :
  - Écartée car : Complexité excessive pour ce projet, nécessite un cluster
- **Docker Swarm** :
  - Écartée car : Docker Compose suffit pour les besoins actuels
- **Déploiement manuel** :
  - Écartée car : Non reproductible, erreurs fréquentes, maintenance difficile

---

## 12. Format de Réponse API

### ✅ Choix : Format hybride (wrapped/unwrapped)

**Décision :** Support de deux formats de réponse : `ApiResponse<T>` (wrapped) et données directes (unwrapped).

**Justification :**
- **Flexibilité** : Compatible avec différents endpoints
- **Rétrocompatibilité** : Supporte les anciens endpoints
- **Cohérence** : Format standardisé pour les nouveaux endpoints

**Alternatives écartées :**
- **Format unique wrapped** :
  - Écartée car : Nécessiterait de modifier tous les endpoints existants
- **Format unique unwrapped** :
  - Écartée car : Moins d'informations (pas de message, pas de statut)

---

## 13. Gestion des Erreurs

### ✅ Choix : Exceptions personnalisées + Response wrapper

**Décision :** Utilisation d'exceptions personnalisées avec un wrapper de réponse standardisé.

**Justification :**
- **Cohérence** : Format d'erreur uniforme
- **Traçabilité** : Messages d'erreur clairs et informatifs
- **Debugging** : Facilite l'identification des problèmes

**Alternatives écartées :**
- **Exceptions Django standard uniquement** :
  - Écartée car : Messages moins informatifs, format moins cohérent

---

## Résumé des Principales Décisions

| Aspect | Choix | Alternative Écartée | Raison Principale |
|--------|-------|-------------------|-------------------|
| Architecture | Monolithique modulaire | Microservices | Simplicité, performance |
| Authentification | JWT Hybride | OAuth2/Sessions | Flexibilité, stateless |
| Quotas | Redis Sorted Sets | PostgreSQL/SQL | Performance, atomicité |
| Verrous | Redis Locks | Optimistic Locking | Atomicité garantie |
| Frontend | Angular Standalone | React/Vue | Spécification projet |
| État | Signals | NgRx | Simplicité, performance |
| Base de données | PostgreSQL | MySQL/MongoDB | ACID, écosystème |
| Cache | Redis | Memcached | Fonctionnalités avancées |
| Déploiement | Docker Compose | Kubernetes | Simplicité |

---

## Points d'Attention et Limitations

1. **Redis comme point de défaillance unique** : 
   - Mitigation : Redis peut être clusterisé, backup RDB/AOF activés

2. **Monolithique peut limiter la scalabilité horizontale** :
   - Mitigation : Architecture modulaire permet migration progressive

3. **JWT sans refresh token** :
   - Limitation : Tokens valides 24h, pas de mécanisme de rafraîchissement
   - Mitigation : Acceptable pour ce cas d'usage, peut être ajouté si nécessaire

4. **Pas de rate limiting global** :
   - Limitation : Seuls les quotas par licence sont appliqués
   - Mitigation : Peut être ajouté avec Django-ratelimit si nécessaire

---

## Conclusion

Les choix techniques effectués privilégient la **simplicité**, la **maintenabilité** et la **performance** tout en gardant la possibilité d'évoluer vers des solutions plus complexes si nécessaire. L'architecture modulaire et l'utilisation de technologies éprouvées garantissent un système robuste et évolutif.

