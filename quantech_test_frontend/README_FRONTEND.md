# Licensing Cloud Management - Frontend Angular 20

Application frontend complète en Angular 20 pour la gestion du système de licensing cloud, construite avec les dernières fonctionnalités d'Angular incluant les **signaux** et le **mode zoneless**.

## 🚀 Fonctionnalités

### 1. **Gestion des Licenses**
- Création de nouvelles licenses avec validation
- Visualisation de toutes les licenses (actives, suspendues, expirées)
- Suspension/Activation des licenses
- Suivi de l'utilisation (applications et exécutions)
- Affichage du token de license
- Suppression de licenses

### 2. **Gestion des Applications**
- Enregistrement de nouvelles applications
- Vérification automatique des quotas (maxApps)
- Filtrage par license
- Visualisation des statistiques par application
- Suppression d'applications

### 3. **Gestion des Jobs**
- Démarrage de nouveaux jobs
- Vérification du quota d'exécutions (24h sliding window)
- Visualisation des jobs (tous / dernières 24h)
- Statistiques détaillées (running, completed, failed)
- Finalisation des jobs (succès/échec)
- Calcul de la durée d'exécution

### 4. **Dashboard**
- Vue d'ensemble avec statistiques en temps réel
- Graphiques et indicateurs visuels
- Actions rapides
- Jobs récents
- Taux de succès calculé

## 🛠 Technologies Utilisées

- **Angular 20** (dernière version)
- **Signaux** pour la gestion d'état réactive
- **Mode Zoneless** pour de meilleures performances
- **Standalone Components** (pas de NgModules)
- **HttpClient** avec fetch API
- **RxJS** pour la gestion asynchrone
- **TypeScript 5.9**
- **SCSS** pour les styles

## 📦 Structure du Projet

```
src/
├── app/
│   ├── components/
│   │   ├── dashboard/
│   │   │   └── dashboard.component.ts
│   │   ├── licenses/
│   │   │   ├── license-list.component.ts
│   │   │   └── license-form.component.ts
│   │   ├── applications/
│   │   │   ├── application-list.component.ts
│   │   │   └── application-form.component.ts
│   │   ├── jobs/
│   │   │   ├── job-list.component.ts
│   │   │   └── job-form.component.ts
│   │   └── navigation/
│   │       └── navbar.component.ts
│   ├── models/
│   │   ├── license.model.ts
│   │   ├── application.model.ts
│   │   ├── job.model.ts
│   │   └── api-response.model.ts
│   ├── services/
│   │   ├── api.service.ts
│   │   ├── license.service.ts
│   │   ├── application.service.ts
│   │   ├── job.service.ts
│   │   ├── license-store.service.ts
│   │   ├── application-store.service.ts
│   │   └── job-store.service.ts
│   ├── app.ts
│   ├── app.html
│   ├── app.scss
│   ├── app.config.ts
│   └── app.routes.ts
└── styles.scss
```

## 🎯 Architecture

### State Management avec Signaux

L'application utilise les **signaux Angular** pour une gestion d'état réactive et performante :

```typescript
// Exemple de store service
private readonly licensesSignal = signal<License[]>([]);
readonly licenses = this.licensesSignal.asReadonly();

// Computed signals
readonly activeLicenses = computed(() =>
  this.licensesSignal().filter(license => license.status === 'ACTIVE')
);
```

### Services

#### API Service
- Service de base pour toutes les requêtes HTTP
- Gestion centralisée des headers et tokens
- Gestion des erreurs

#### Store Services
- **LicenseStoreService** : Gestion d'état pour les licenses
- **ApplicationStoreService** : Gestion d'état pour les applications
- **JobStoreService** : Gestion d'état pour les jobs

Chaque store fournit :
- Signaux réactifs en lecture seule
- Computed signals pour les données dérivées
- Actions pour modifier l'état

## 🔧 Configuration

### Variables d'Environnement

L'URL de l'API backend est configurée dans `api.service.ts` :

```typescript
private readonly baseUrl = 'http://localhost:8080/api';
```

Modifiez cette URL selon votre configuration backend.

## 📱 Responsive Design

L'application est entièrement responsive avec des breakpoints pour :
- Desktop (> 768px)
- Tablet (768px)
- Mobile (< 768px)

## 🚦 Installation et Démarrage

### Prérequis
- Node.js 20+
- npm ou yarn

### Installation

```bash
npm install
```

### Développement

```bash
npm start
# ou
ng serve
```

L'application sera accessible sur `http://localhost:4200`

### Build de Production

```bash
npm run build
# ou
ng build
```

Les fichiers de production seront dans le dossier `dist/`

## 🔗 Endpoints API

L'application communique avec le backend via les endpoints suivants :

### Licenses
- `GET /api/licenses` - Liste toutes les licenses
- `POST /api/licenses` - Créer une nouvelle license
- `GET /api/licenses/:id` - Récupérer une license
- `PUT /api/licenses/:id` - Mettre à jour une license
- `PUT /api/licenses/:id/suspend` - Suspendre une license
- `PUT /api/licenses/:id/activate` - Activer une license
- `DELETE /api/licenses/:id` - Supprimer une license
- `GET /api/licenses/usage` - Récupérer l'utilisation (avec token)

### Applications
- `GET /api/apps` - Liste toutes les applications
- `POST /api/apps/register` - Enregistrer une application
- `GET /api/apps/:id` - Récupérer une application
- `GET /api/apps/license/:licenseId` - Applications par license
- `PUT /api/apps/:id` - Mettre à jour une application
- `DELETE /api/apps/:id` - Supprimer une application

### Jobs
- `GET /api/jobs` - Liste tous les jobs
- `POST /api/jobs/start` - Démarrer un job
- `POST /api/jobs/finish` - Finaliser un job
- `GET /api/jobs/:id` - Récupérer un job
- `GET /api/jobs/application/:appId` - Jobs par application
- `GET /api/jobs/stats` - Statistiques des jobs
- `GET /api/jobs/last24h` - Jobs des dernières 24h

## 🎨 Design System

### Couleurs Principales

- **Primary**: Gradient violet (#667eea → #764ba2)
- **Success**: Gradient vert (#43e97b → #38f9d7)
- **Warning**: Jaune (#ffc107)
- **Danger**: Rouge (#dc3545)
- **Info**: Gradient bleu (#4facfe → #00f2fe)

### Composants

Tous les composants utilisent :
- Standalone components
- Template inline avec backticks
- Styles inline avec SCSS
- Signaux pour la réactivité

## 🧪 Test du Scénario

Pour tester le scénario décrit dans le challenge :

1. **Créer une license** : tenant "acme", 2 apps max, 100 exécutions/24h
2. **Enregistrer 2 applications** → ✅ Succès
3. **Tenter d'enregistrer une 3ème app** → ❌ Rejet (quota atteint)
4. **Exécuter 100 jobs** → ✅ Succès
5. **Tenter le 101ème job** → ❌ Rejet (quota exécutions atteint)

## 📝 Modèles de Données

### License
```typescript
interface License {
  id?: string;
  tenant: string;
  maxApps: number;
  maxExecutionsPer24h: number;
  validFrom: string;
  validTo: string;
  status: LicenseStatus; // ACTIVE | SUSPENDED | EXPIRED | REVOKED
  token?: string;
}
```

### Application
```typescript
interface Application {
  id?: string;
  name: string;
  description?: string;
  licenseId?: string;
  tenant?: string;
}
```

### Job
```typescript
interface Job {
  id?: string;
  applicationId: string;
  status: JobStatus; // PENDING | RUNNING | COMPLETED | FAILED
  startedAt?: string;
  finishedAt?: string;
  duration?: number;
  errorMessage?: string;
  metadata?: Record<string, any>;
}
```

## 🔐 Sécurité

- Validation des tokens côté serveur
- Aucune manipulation de token côté client
- Gestion sécurisée des erreurs
- Validation des formulaires

## 🚀 Optimisations

- **Lazy Loading** des routes
- **Signals** pour une réactivité optimale
- **Zoneless mode** pour de meilleures performances
- **Standalone components** pour un bundle size réduit
- **OnPush change detection** via les signaux

## 📚 Ressources

- [Angular 20 Documentation](https://angular.dev)
- [Angular Signals](https://angular.dev/guide/signals)
- [Standalone Components](https://angular.dev/guide/standalone-components)

## 👨‍💻 Développement

Le projet respecte toutes les exigences du challenge :
- ✅ Vérification des quotas (apps et exécutions)
- ✅ Fenêtre glissante de 24h pour les exécutions
- ✅ Gestion des statuts de license
- ✅ Validation et vérification des tokens
- ✅ Interface utilisateur complète et intuitive
- ✅ Architecture moderne avec Angular 20
- ✅ Utilisation des signaux et mode zoneless

---

**Note**: Assurez-vous que le backend est démarré avant de lancer l'application frontend.
