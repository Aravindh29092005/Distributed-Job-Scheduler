import React from 'react';
import { Navigate } from 'react-router-dom';
import LoginPage from './pages/Login';
import DashboardPage from './pages/Dashboard';
import OrganizationsPage from './pages/OrganizationsPage';
import ProjectsPage from './pages/Projects';
import QueuesPage from './pages/Queues';
import QueueDetailsPage from './pages/QueueDetails';
import JobsPage from './pages/Jobs';
import JobDetailPage from './pages/JobDetails';
import WorkersPage from './pages/Workers';
import DeadLetterQueuePage from './pages/DeadLetterQueue';
import MetricsPage from './pages/Metrics';

export const routes = [
  { path: '/login', element: <LoginPage /> },
  { path: '/dashboard', element: <DashboardPage /> },
  { path: '/organizations', element: <OrganizationsPage /> },
  { path: '/projects', element: <ProjectsPage /> },
  { path: '/queues', element: <QueuesPage /> },
  { path: '/queues/:queueId', element: <QueueDetailsPage /> },
  { path: '/jobs', element: <JobsPage /> },
  { path: '/jobs/:jobId', element: <JobDetailPage /> },
  { path: '/workers', element: <WorkersPage /> },
  { path: '/dlq', element: <DeadLetterQueuePage /> },
  { path: '/metrics', element: <MetricsPage /> },
];
