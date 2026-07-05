# Codity Frontend

React + TypeScript + Vite frontend for the Distributed Job Scheduling Platform.

## Features

- **10 Pages**: Login, Dashboard, Organizations, Projects, Queues, Jobs, Job Details, Workers, DLQ, Metrics
- **Live Updates**: HTTP polling with configurable intervals (WebSockets planned)
- **Job Details**: Unified view with lifecycle timeline, execution logs, and retry history
- **Responsive Design**: Built with Tailwind CSS

## Polling Configuration

```
- Jobs List: 3s
- Job Details: 2s (for active monitoring)
- Workers: 5s
- Metrics: 5s
- Queues: 10s
- Dead Letter Queue: 10s
```

> Note: WebSockets are planned as a future improvement for real-time updates.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:3000` with proxy to `http://localhost:8000/api`

## Build

```bash
npm run build
```

## Architecture

- **Services**: API client with polling intervals defined
- **Hooks**: `usePolling` for automatic refetching
- **Components**: Reusable UI components (JobTimeline, ExecutionLogs, RetryHistory)
- **Pages**: Full-page components for each route
- **Utils**: Store (Zustand), date formatting, status badges

## API Integration

The frontend expects these endpoints:

```
POST   /auth/login
GET    /auth/me

GET    /organizations
POST   /organizations
PUT    /organizations/{id}
DELETE /organizations/{id}

GET    /projects
POST   /projects
PUT    /projects/{id}
DELETE /projects/{id}

GET    /queues
POST   /queues
PUT    /queues/{id}
DELETE /queues/{id}

GET    /jobs
GET    /jobs/{id}
POST   /jobs
PUT    /jobs/{id}
DELETE /jobs/{id}
GET    /jobs/{id}/executions
GET    /jobs/{id}/logs
GET    /jobs/{id}/retries

GET    /workers
GET    /workers/{id}
GET    /workers/{id}/metrics

GET    /dlq
GET    /dlq/{id}
POST   /dlq/{id}/retry
DELETE /dlq/{id}

GET    /metrics/dashboard
GET    /metrics/jobs
GET    /metrics/workers
GET    /metrics/queues
```

## Future Improvements

- WebSocket support for real-time updates (replaces polling)
- Advanced filtering and search
- Export job execution reports
- Custom dashboards
- Dark mode support
