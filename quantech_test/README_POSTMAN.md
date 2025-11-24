# Guide d'utilisation de la Collection Postman

## 📦 Fichier de la Collection

La collection Postman complète est disponible dans :
```
quantech_test/Postman_Collection_Complete.json
```

## 🚀 Installation

### Méthode 1 : Import dans Postman

1. Ouvrir **Postman**
2. Cliquer sur **Import** (en haut à gauche)
3. Sélectionner le fichier `Postman_Collection_Complete.json`
4. La collection sera importée avec toutes les requêtes organisées

### Méthode 2 : Import via URL (si hébergé)

1. Dans Postman, cliquer sur **Import**
2. Sélectionner l'onglet **Link**
3. Coller l'URL de la collection (si disponible)

## ⚙️ Configuration

### Variables de Collection

La collection utilise les variables suivantes qui sont automatiquement remplies :

| Variable | Description | Remplie automatiquement |
|----------|-------------|------------------------|
| `base_url` | URL de base de l'API | `http://localhost:8000/api` |
| `user_token` | Token JWT de l'utilisateur | Après login/register |
| `license_token` | Token JWT de la licence | Après création de licence |
| `license_id` | ID de la licence | Après création de licence |
| `application_id` | ID de l'application | Après enregistrement |
| `job_id` | ID du job | Après démarrage d'un job |

### Modification de l'URL de base

Si votre API est hébergée ailleurs :

1. Ouvrir la collection dans Postman
2. Cliquer sur les **...** à côté du nom de la collection
3. Sélectionner **Edit**
4. Aller dans l'onglet **Variables**
5. Modifier la valeur de `base_url`

## 📋 Structure de la Collection

La collection est organisée en 5 sections principales :

### 0. Health Check
- **GET /health/** - Vérifier l'état de santé de l'API

### 1. Authentication
- **POST /auth/register/** - Créer un compte utilisateur
- **POST /auth/login/** - Se connecter
- **GET /auth/me/** - Obtenir les infos de l'utilisateur connecté
- **POST /auth/refresh/** - Rafraîchir le token
- **POST /auth/logout/** - Se déconnecter

### 2. Licenses
- **GET /licenses/** - Lister toutes les licences
- **POST /licenses/** - Créer une nouvelle licence
- **GET /licenses/{id}/** - Détails d'une licence
- **PUT /licenses/{id}/** - Mettre à jour une licence
- **DELETE /licenses/{id}/** - Révoquer une licence
- **POST /licenses/{id}/suspend/** - Suspendre une licence
- **DELETE /licenses/{id}/suspend/** - Réactiver une licence
- **POST /licenses/{id}/upgrade/** - Mettre à niveau les quotas
- **GET /licenses/{id}/history/** - Historique des modifications
- **POST /tokens/generate/** - Générer un nouveau token
- **GET /quota/status/** - Statut des quotas (licence authentifiée)
- **GET /licenses/{id}/quota-status/** - Statut des quotas (par ID)

### 3. Applications
- **POST /apps/register** - Enregistrer une application (endpoint public)
- **GET /applications/** - Lister toutes les applications
- **GET /applications/{id}/** - Détails d'une application
- **PUT /applications/{id}/** - Mettre à jour une application
- **DELETE /applications/{id}/** - Désactiver/supprimer une application
- **POST /applications/{id}/activate/** - Activer une application
- **GET /applications/{id}/metrics/** - Métriques d'une application
- **GET /applications/metrics/** - Métriques de toutes les applications
- **POST /apps/register** (Test Quota) - Tester le quota max_apps

### 4. Jobs
- **POST /jobs/start** - Démarrer un job (endpoint public)
- **POST /jobs/finish** - Terminer un job (endpoint public)
- **GET /jobs/** - Lister tous les jobs
- **GET /jobs/{id}/** - Détails d'un job
- **GET /jobs/statistics/** - Statistiques des jobs
- **GET /executions/window/** - Fenêtre d'exécution (24h)
- **POST /jobs/start** (Test Quota) - Tester le quota max_executions_per_24h

### 5. Scénarios de Test Complets
- **Scénario Complet - Workflow Standard** : Workflow complet de bout en bout
- **Scénario - Test Quota Applications** : Test du quota max_apps
- **Scénario - Test Quota Exécutions** : Test du quota max_executions_per_24h

## 🔄 Utilisation

### Workflow Standard

1. **Health Check** : Vérifier que l'API est accessible
2. **Register/Login** : Créer un compte ou se connecter
   - Le token utilisateur est automatiquement sauvegardé
3. **Create License** : Créer une licence
   - Le token de licence et l'ID sont automatiquement sauvegardés
4. **Register Application** : Enregistrer une application
   - L'ID de l'application est automatiquement sauvegardé
5. **Start Job** : Démarrer un job
   - L'ID du job est automatiquement sauvegardé
6. **Finish Job** : Terminer le job

### Tests Automatiques

Chaque requête contient des scripts de test qui :
- Vérifient les codes de statut HTTP
- Valident la structure des réponses
- Sauvegardent automatiquement les tokens et IDs dans les variables

### Exécution de Scénarios

Les scénarios de test complets peuvent être exécutés avec **Postman Runner** :

1. Ouvrir **Postman Runner** (icône en haut)
2. Sélectionner la collection
3. Choisir le scénario à exécuter
4. Cliquer sur **Run**

## 🧪 Tests de Validation

### Test 1 : Quota d'Applications

1. Créer une licence avec `max_apps: 2`
2. Enregistrer 2 applications (doivent réussir)
3. Enregistrer une 3ème application (doit échouer avec 400/429)

### Test 2 : Quota d'Exécutions (24h)

1. Créer une licence avec `max_executions_per_24h: 5`
2. Démarrer 5 jobs (doivent réussir)
3. Démarrer un 6ème job (doit échouer avec 429)

### Test 3 : Authentification

1. Tester avec token valide (doit réussir)
2. Tester avec token invalide (doit retourner 401)
3. Tester sans token (doit retourner 401)

## 📝 Notes Importantes

### Tokens JWT

- **User Token** : Utilisé pour les opérations administratives (créer des licences, etc.)
- **License Token** : Utilisé pour les opérations liées aux applications et jobs
- Les tokens sont valides pendant 24 heures par défaut

### Codes de Statut

| Code | Signification |
|------|---------------|
| 200 | Succès |
| 201 | Créé avec succès |
| 400 | Requête invalide (quota dépassé, données manquantes) |
| 401 | Non authentifié |
| 403 | Interdit (licence suspendue) |
| 404 | Non trouvé |
| 429 | Trop de requêtes (quota d'exécutions dépassé) |
| 500 | Erreur serveur |

### Format des Dates

Toutes les dates doivent être au format ISO 8601 (UTC) :
```
2025-01-01T00:00:00Z
```

### Headers Requis

- **Content-Type** : `application/json` (pour les requêtes POST/PUT)
- **Authorization** : `Bearer {token}` (pour les endpoints protégés)

## 🔍 Dépannage

### Erreur : "Connection refused"

**Solution** : Vérifier que les services Docker sont démarrés
```bash
docker compose ps
docker compose up -d
```

### Erreur : "401 Unauthorized"

**Solution** : 
- Vérifier que le token est valide
- Se reconnecter pour obtenir un nouveau token
- Vérifier que le header Authorization est correctement formaté

### Erreur : "400 Bad Request"

**Solution** :
- Vérifier le format JSON du body
- Vérifier que tous les champs requis sont présents
- Vérifier les types de données (UUID, dates, etc.)

### Variables non remplies

**Solution** :
- Exécuter les requêtes dans l'ordre (register → create license → etc.)
- Vérifier que les scripts de test s'exécutent correctement
- Vérifier la console Postman pour les erreurs JavaScript

## 📚 Ressources

- **Documentation API** : Voir `VALIDATION_API.md` pour les commandes cURL
- **Choix techniques** : Voir `CHOIX_TECHNIQUES.md` pour l'architecture
- **Collection originale** : `Licensing_API.postman_collection.json` (version simplifiée)

## 🎯 Prochaines Étapes

1. Importer la collection dans Postman
2. Configurer la variable `base_url` si nécessaire
3. Exécuter le scénario "Workflow Standard" pour valider le système
4. Tester les quotas avec les scénarios dédiés

