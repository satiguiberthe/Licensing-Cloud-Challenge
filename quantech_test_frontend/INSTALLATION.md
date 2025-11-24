# Guide d'Installation - Frontend Licensing Cloud

## 📋 Prérequis

- **Node.js** 20 ou supérieur
- **npm** 10 ou supérieur
- **Backend** de l'API en cours d'exécution sur `http://localhost:8080`

## 🚀 Installation

### 1. Cloner et accéder au projet

```bash
cd /Users/satiguiberthe/Desktop/Dev/frontend/quantech_test
```

### 2. Installer les dépendances

```bash
npm install
```

### 3. Configuration de l'API

Par défaut, l'application pointe vers `http://localhost:8080/api`.

Pour modifier l'URL de l'API, éditez le fichier :
```
src/src/app/services/api.service.ts
```

Ligne 12 :
```typescript
private readonly baseUrl = 'http://localhost:8080/api';
```

### 4. Démarrer l'application en mode développement

```bash
npm start
```

L'application sera accessible sur **http://localhost:4200**

### 5. Build de production

```bash
npm run build
```

Les fichiers de production seront générés dans `dist/src/browser/`

## 📁 Structure du Projet

```
src/
├── src/
│   ├── app/
│   │   ├── components/          # Tous les composants
│   │   │   ├── dashboard/       # Dashboard principal
│   │   │   ├── licenses/        # Gestion des licenses
│   │   │   ├── applications/    # Gestion des applications
│   │   │   ├── jobs/            # Gestion des jobs
│   │   │   └── navigation/      # Navbar
│   │   ├── models/              # Interfaces TypeScript
│   │   ├── services/            # Services API et stores
│   │   ├── app.ts               # Composant racine
│   │   ├── app.config.ts        # Configuration Angular
│   │   └── app.routes.ts        # Routes de l'app
│   ├── styles.scss              # Styles globaux
│   └── index.html               # Point d'entrée HTML
├── package.json
└── angular.json                 # Configuration Angular CLI
```

## 🎯 Fonctionnalités Implémentées

### ✅ Dashboard
- Vue d'ensemble avec statistiques en temps réel
- Cartes de statistiques (licenses, apps, jobs)
- Graphiques de statut des jobs
- Actions rapides
- Liste des jobs récents

### ✅ Gestion des Licenses
- Création de nouvelles licenses
- Liste avec filtres (actives, expirées)
- Suspension/Activation
- Suivi de l'utilisation (quotas apps et exécutions)
- Suppression

### ✅ Gestion des Applications
- Enregistrement avec validation de quota
- Filtrage par license
- Liste avec statistiques
- Suppression

### ✅ Gestion des Jobs
- Démarrage avec validation de quota 24h
- Filtrage (tous / dernières 24h)
- Finalisation (succès/échec)
- Statistiques complètes
- Calcul de durée

## 🔧 Technologies

- **Angular 20.3.0** - Framework frontend
- **TypeScript 5.9** - Langage
- **RxJS 7.8** - Programmation réactive
- **SCSS** - Styles
- **Signaux Angular** - Gestion d'état
- **Mode Zoneless** - Performances optimisées
- **Standalone Components** - Architecture moderne

## 🌐 Routes Disponibles

| Route | Description |
|-------|-------------|
| `/` | Redirection vers `/dashboard` |
| `/dashboard` | Tableau de bord principal |
| `/licenses` | Gestion des licenses |
| `/applications` | Gestion des applications |
| `/jobs` | Gestion des jobs |

## 🧪 Scénario de Test

Pour valider le système selon le challenge :

### 1. Créer une License
- Aller sur `/licenses`
- Cliquer sur "Create License"
- Remplir :
  - Tenant: `acme`
  - Max Apps: `2`
  - Max Executions/24h: `100`
  - Valid From: Date actuelle
  - Valid To: Date future
  - Status: `ACTIVE`
- Soumettre

### 2. Enregistrer 2 Applications
- Aller sur `/applications`
- Cliquer sur "Register Application"
- Sélectionner la license "acme"
- Enregistrer 2 apps → ✅ Succès

### 3. Tenter une 3ème Application
- Essayer d'enregistrer une 3ème app
- → ❌ Erreur : Quota atteint (maxApps = 2)

### 4. Exécuter 100 Jobs
- Aller sur `/jobs`
- Cliquer sur "Start New Job"
- Sélectionner une app et la license
- Répéter 100 fois → ✅ Succès

### 5. Tenter le 101ème Job
- Essayer de démarrer un 101ème job
- → ❌ Erreur : Quota d'exécutions atteint (maxExecutionsPer24h = 100)

## 📊 API Endpoints Utilisés

### Licenses
- `GET /api/licenses` - Liste
- `POST /api/licenses` - Création
- `PUT /api/licenses/:id` - Mise à jour
- `PUT /api/licenses/:id/suspend` - Suspension
- `PUT /api/licenses/:id/activate` - Activation
- `DELETE /api/licenses/:id` - Suppression
- `GET /api/licenses/usage` - Utilisation (avec token)

### Applications
- `GET /api/apps` - Liste
- `POST /api/apps/register` - Enregistrement
- `GET /api/apps/license/:id` - Par license
- `DELETE /api/apps/:id` - Suppression

### Jobs
- `GET /api/jobs` - Liste
- `POST /api/jobs/start` - Démarrage
- `POST /api/jobs/finish` - Finalisation
- `GET /api/jobs/stats` - Statistiques
- `GET /api/jobs/last24h` - Dernières 24h

## 🎨 Design

L'interface utilise :
- **Gradients modernes** pour les cartes
- **Design Material** inspiré
- **Responsive** (mobile, tablet, desktop)
- **Animations** fluides
- **Couleurs thématiques** par section

## ⚡ Optimisations

- **Lazy Loading** des routes
- **Signaux** pour réactivité optimale
- **Change Detection** optimisée (zoneless)
- **Standalone Components** (pas de NgModules)
- **Tree Shaking** automatique

## 🐛 Dépannage

### L'application ne démarre pas
```bash
# Nettoyer et réinstaller
rm -rf node_modules package-lock.json
npm install
npm start
```

### Erreurs de connexion API
1. Vérifier que le backend est démarré sur `http://localhost:8080`
2. Vérifier les CORS côté backend
3. Vérifier la configuration dans `api.service.ts`

### Erreurs de build
```bash
# Nettoyer le cache Angular
npx ng cache clean
npm run build
```

## 📝 Notes Importantes

1. **Backend requis** : L'application ne fonctionnera pas sans le backend
2. **CORS** : Le backend doit autoriser `http://localhost:4200`
3. **Tokens** : Tous les appels sensibles nécessitent un token de license valide
4. **Fenêtre glissante 24h** : Le backend doit implémenter cette logique

## 🚀 Déploiement

### Build de production
```bash
npm run build
```

### Servir avec un serveur HTTP
```bash
npx http-server dist/src/browser -p 8080
```

### Avec Docker (optionnel)
```dockerfile
FROM nginx:alpine
COPY dist/src/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 📚 Ressources

- [Angular Documentation](https://angular.dev)
- [Angular Signals Guide](https://angular.dev/guide/signals)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Dernière mise à jour** : 24 Novembre 2025
**Version Angular** : 20.3.0
**Status** : ✅ Production Ready
