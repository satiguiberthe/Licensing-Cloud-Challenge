# Licensing Cloud Challenge

## 1. Objectif

Ce projet implémente un **système de gestion de licences cloud** permettant de limiter l'usage d'une plateforme selon les droits attribués à chaque client.

Chaque **client** dispose d'une **licence numérique** définissant notamment :

* le nombre maximum d'applications pouvant être enregistrées (`maxApps`) ;
* le nombre maximum d'exécutions autorisées sur une période de 24 heures glissantes (`maxExecutionsPer24h`).

Le système garantit que ces limites ne puissent pas être dépassées, même en cas d'appels concurrents.

---

## 2. Contexte général

La plateforme exécute des traitements ("jobs") pour le compte de clients identifiés par leur licence. Une application peut embarquer plusieurs jobs et un job est défini pour une et une seule application.

Chaque requête effectuée par un client est accompagnée d'un jeton représentant sa licence.  
Ce jeton contient les informations nécessaires à la vérification de ses droits (identité, limites, période de validité, statut, etc.).

Le système :

1. Vérifie la **validité** de la licence (authenticité, date de validité, statut actif).
2. Applique les **restrictions** d'usage définies par la licence.
3. Empêche toute exécution supplémentaire en cas de dépassement de quota.

---

## 3. Fonctionnalités implémentées

Le projet expose les endpoints suivants :

| Endpoint            | Description                                                                                          |
| ------------------- | ---------------------------------------------------------------------------------------------------- |
| POST /apps/register | Enregistre une nouvelle application pour le client. Refuse l'opération si maxApps est atteint. |
| POST /jobs/start    | Démarre une exécution (vérifie le quota 24h).                                                        |
| POST /jobs/finish   | Termine une exécution.                                                                               |

**Comportements implémentés :**

* ✅ Une requête au-delà du quota autorisé est refusée.
* ✅ Les exécutions plus anciennes que 24 heures ne sont plus comptabilisées.
* ✅ Une licence expirée ou révoquée bloque toute opération.

---

## 4. Sécurité

La gestion des licences est sécurisée :

* ✅ **Signature et vérification** côté serveur (aucune confiance côté client) ;
* ✅ Dates de validité (`validFrom`, `validTo`) et état de la licence (`ACTIVE`, `SUSPENDED`, etc.) inclus ;
* ✅ Protection des communications et des échanges de clés ;
* ✅ Protection contre la falsification du jeton (JWT avec signature HS256).

---

## 5. Fenêtre glissante

Le quota `maxExecutionsPer24h` est appliqué sur une **fenêtre glissante de 24 heures** :  
le système ne compte que les exécutions réalisées dans les 24 dernières heures, à partir de l'instant courant.  
Les exécutions plus anciennes sont ignorées automatiquement.

**Mécanisme choisi :** Redis avec Sorted Sets (ZSET) pour une performance optimale et une atomicité garantie.

Voir [CHOIX_TECHNIQUES.md](CHOIX_TECHNIQUES.md) pour plus de détails.

---

## 6. Architecture et choix techniques

### Stack technique

* **Backend** : Django 5.0.1 + Django REST Framework
* **Base de données** : PostgreSQL 15
* **Cache/Quotas** : Redis 7 (Sorted Sets pour fenêtre glissante)
* **Frontend** : Angular 18+ (Standalone Components)
* **Tâches asynchrones** : Celery 5.3.4
* **Conteneurisation** : Docker + Docker Compose

### Structure du projet

```
licensing-cloud-challenge/
├── README.md                 # Ce document
├── CHOIX_TECHNIQUES.md       # Analyse technique détaillée
├── docker-compose.yml        # Orchestration des services
├── quantech_test/            # Backend Django (API principale)
│   ├── src/
│   │   ├── applications/     # Gestion des applications
│   │   ├── jobs/             # Gestion des jobs
│   │   ├── licenses/         # Gestion des licences
│   │   ├── utility/          # Services utilitaires (quotas, auth)
│   │   └── ...
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── requirements.txt
│   └── README.md
├── quantech_test_frontend/   # Frontend Angular
│   ├── src/
│   ├── Dockerfile
│   └── README.md
└── tests/
    └── scenario.postman.json # Scénarios de test
```

**Note :** La structure suggérée dans le challenge (gateway/, licensing-service/, metering-service/) a été adaptée en une architecture monolithique modulaire pour simplifier le déploiement et la maintenance. Voir [CHOIX_TECHNIQUES.md](CHOIX_TECHNIQUES.md) pour la justification.

---

## 7. Démarrage rapide

### Prérequis

- Docker Desktop (ou Docker Engine + Docker Compose)
- Ports 8000 (backend) et 4200 (frontend) disponibles

### Lancement

```bash
docker compose up --build
```

Le système sera disponible à :
- **Backend API** : http://localhost:8000
- **Frontend** : http://localhost:4200

### Services démarrés

- **backend** : Django API (port 8000)
- **frontend** : Angular application (port 4200)
- **db** : PostgreSQL database (port 5433)
- **redis** : Redis cache et quotas (port 6379)
- **celery** : Worker pour tâches asynchrones
- **celery-beat** : Planificateur de tâches

### Identifiants administrateur

Pour accéder à l'interface d'administration Django :

- **Username** : `admin`
- **Password** : `admin123456`

L'interface d'administration est accessible à : http://localhost:8000/admin/

---

## 8. Scénario de test

Un scénario complet est disponible dans [tests/scenario.postman.json](tests/scenario.postman.json).

### Scénario manuel

1. **Création d'une licence** :
```json
POST /api/licenses/
{
  "tenant_id": "acme",
  "maxApps": 2,
  "maxExecutionsPer24h": 100,
  "validFrom": "2025-11-01T00:00:00Z",
  "validTo": "2025-12-01T00:00:00Z",
  "status": "ACTIVE"
}
```

2. **Enregistrement de deux applications** → ✅ accepté
3. **Tentative d'enregistrement d'une troisième** → ❌ refusée (maxApps atteint)
4. **Exécution de 100 jobs sur 24 heures** → ✅ accepté
5. **101ᵉ exécution dans la même période** → ❌ refusée (quota dépassé)

---

## 9. Tests

### Collection Postman

Importez la collection Postman disponible dans :
- `tests/scenario.postman.json` (scénario de test complet)
- `quantech_test/Licensing_API.postman_collection.json` (collection complète de l'API)

### Tests automatisés

```bash
# Exécuter les tests Django
docker compose exec backend python manage.py test

# Tests de charge (exemple avec Apache Bench)
ab -n 1000 -c 50 -H "Authorization: Bearer <token>" \
   -p job.json -T application/json \
   http://localhost:8000/api/jobs/start
```

---

## 10. Documentation

- **Choix techniques** : [CHOIX_TECHNIQUES.md](CHOIX_TECHNIQUES.md) - Analyse détaillée des décisions architecturales
- **Backend** : [quantech_test/README.md](quantech_test/README.md) - Documentation de l'API
- **Frontend** : [quantech_test_frontend/README.md](quantech_test_frontend/README.md) - Documentation du frontend
- **API Tests** : [tests/scenario.postman.json](tests/scenario.postman.json) - Scénarios de test

---

## 11. Évaluation

### Points forts

* ✅ **Robustesse** : Prévention des conditions de course avec verrous distribués Redis
* ✅ **Sécurité** : Vérification JWT côté serveur, protection contre la falsification
* ✅ **Performance** : Redis Sorted Sets pour fenêtre glissante efficace
* ✅ **Cohérence** : Transactions ACID, atomicité garantie
* ✅ **Qualité du code** : Structure modulaire, documentation complète
* ✅ **Reproductibilité** : Docker Compose, démarrage en une commande
* ✅ **Tests** : Collection Postman complète avec scénarios de test

### Améliorations possibles

* Interface d'administration pour la gestion des licences (déjà implémentée via Django Admin)
* Monitoring avancé (Prometheus + Grafana)
* Rate limiting global en plus des quotas par licence
* Refresh tokens pour les JWT
* Migration vers architecture microservices si nécessaire

---

## 12. Référence

Ce projet répond au challenge technique disponible sur :
https://github.com/ranoquantech/licensing-cloud-challenge

---

## 13. Auteur

Développé pour le Licensing Cloud Challenge

**Durée de développement** : 5 jours  
**Focus** : Sécurité, prévention des conditions de course, précision de la fenêtre glissante

---

## 14. Licence

MIT License

