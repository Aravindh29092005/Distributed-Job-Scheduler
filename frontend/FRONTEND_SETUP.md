# Frontend Setup & Running Guide

## Directory Structure

```
frontend/
├── src/
│   ├── pages/                    # Full page components
│   │   ├── LoginPage.tsx         # Authentication
│   │   ├── DashboardPage.tsx     # Main dashboard with metrics
│   │   ├── OrganizationsPage.tsx # Organization management
│   │   ├── ProjectsPage.tsx      # Project management
│   │   ├── QueuesPage.tsx        # Queue listing & status
│   │   ├── JobsPage.tsx          # Jobs list with polling (3s)
│   │   ├── JobDetailPage.tsx     # Job detail with timeline, logs, retries
│   │   ├── WorkersPage.tsx       # Worker status & metrics
│   │   ├── DeadLetterQueuePage.tsx # Failed jobs management
│   │   └── MetricsPage.tsx       # System metrics & analytics
│   │
│   ├── components/               # Reusable UI components
│   │   ├── Header.tsx            # Top navigation bar
│   │   ├── Sidebar.tsx           # Side navigation
│   │   ├── StatusBadge.tsx       # Status display component
│   │   ├── JobTimeline.tsx       # Lifecycle timeline visualization
│   │   ├── ExecutionLogs.tsx     # Log viewer with levels
│   │   └── RetryHistory.tsx      # Retry attempts table
│   │
│   ├── services/                 # API integration
│   │   ├── api.ts                # Axios client setup
│   │   └── index.ts              # All API endpoints + polling config
│   │
│   ├── hooks/                    # Custom React hooks
│   │   └── usePolling.ts         # Polling hook for live updates
│   │
│   ├── utils/                    # Utilities
│   │   ├── store.ts              # Zustand stores (Auth, UI)
│   │   ├── date.ts               # Date formatting utilities
│   │   └── status.ts             # Status badge colors & labels
│   │
│   ├── App.tsx                   # Main app with routing
│   ├── main.tsx                  # React entry point
│   └── index.css                 # Tailwind imports & custom styles
│
├── public/                       # Static assets
├── package.json                  # Dependencies
├── vite.config.ts               # Vite configuration with proxy
├── tsconfig.json                # TypeScript config
├── tailwind.config.js           # Tailwind CSS config
├── postcss.config.js            # PostCSS config
└── README.md                    # Frontend documentation
```

## Installation

```bash
cd frontend
npm install
```

## Development Server

```bash
npm run dev
```

**Access:** http://localhost:3000

The frontend automatically proxies API calls from `/api/*` to `http://localhost:8000/*`

## Build for Production

```bash
npm run build
```

Output: `frontend/dist/`

## Live Updates - Polling Strategy

Instead of WebSockets (planned for v2), the frontend uses **HTTP polling** with the following intervals:

| Resource | Interval | Use Case |
|----------|----------|----------|
| Jobs List | 3s | Quickly see new/updated jobs |
| Job Detail | 2s | Real-time monitoring during execution |
| Workers | 5s | Worker availability & load |
| Metrics | 5s | Dashboard metrics refresh |
| Queues | 10s | Queue depth updates |
| Dead Letter Queue | 10s | Failed job visibility |

### Polling Implementation

The `usePolling` hook automatically:
- Fetches data at the configured interval
- Handles errors gracefully
- Cleans up on component unmount
- Can be toggled on/off with `enabled` prop

Example:
```typescript
const { data, loading, error, refetch } = usePolling(
  () => jobsService.list().then(res => res.data),
  { interval: POLLING_INTERVALS.JOBS_LIST }
);
```

## Key Features

### 1. **Job Detail Page** - Unified View
Combines three sections in one view:

```
┌─────────────────────────────────────────────┐
│ Job: email-notification-123  [RUNNING]     │
│ Created: 2026-07-04 10:30:00                │
└─────────────────────────────────────────────┘

Left Column              │  Right Column
──────────────────────  │  ──────────────────
Lifecycle Timeline      │  Execution Logs
- Pending (10:30:00)    │  [INFO] Job started
- Running (10:30:05)    │  [DEBUG] Processing...
  Duration: 5s          │  [ERROR] Timeout after 30s
- Failed (10:30:35)     │
  Error: Timeout        │  Retry History
                        │  Attempt #1: Failed
                        │  Attempt #2: Failed
                        │  Attempt #3: Running (next)
```

### 2. **Responsive Design**
- Desktop: Full sidebar + content
- Tablet: Collapsed sidebar
- Mobile: Hidden sidebar (collapsible)

### 3. **Authentication**
- Login page at `/login`
- Token stored in localStorage
- Auto-redirect to login if not authenticated
- Logout clears token

### 4. **Status Management**
- Zustand stores for Auth & UI state
- Centralized token management
- Current org/project tracking

## Environment

The frontend expects the backend API at `http://localhost:8000`

Proxy configuration in `vite.config.ts`:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '')
  }
}
```

## Future Improvements

1. **WebSocket Support** - Replace polling with real-time updates
2. **Advanced Filtering** - Jobs, queues, workers with complex filters
3. **Export Reports** - Download job execution reports (CSV, PDF)
4. **Custom Dashboards** - Configurable dashboard widgets
5. **Dark Mode** - Theme toggle
6. **Notifications** - Toast/alert system for errors
7. **Job Scheduling UI** - Create and schedule jobs from UI

## Troubleshooting

### API Not Responding
- Ensure backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify `vite.config.ts` proxy configuration

### Pages Not Loading
- Check browser console for TypeScript errors
- Verify all routes are defined in `App.tsx`
- Check that all API endpoints exist in backend

### Polling Too Frequent/Slow
- Adjust intervals in `src/services/index.ts` (`POLLING_INTERVALS`)
- Higher interval = less frequent updates, better performance
- Lower interval = more real-time, higher server load

## Tech Stack

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool (fast dev server)
- **React Router v6**: Client-side routing
- **Axios**: HTTP client
- **Zustand**: State management
- **Tailwind CSS**: Styling
- **Lucide React**: Icons
