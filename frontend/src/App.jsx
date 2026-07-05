import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { OrganizationsPage } from './pages/OrganizationsPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { QueuesPage } from './pages/QueuesPage';
import { JobsPage } from './pages/JobsPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { WorkersPage } from './pages/WorkersPage';
import { DeadLetterQueuePage } from './pages/DeadLetterQueuePage';
import { MetricsPage } from './pages/MetricsPage';
import { useAuthStore } from './utils/store';

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="app-shell">
                <Sidebar />
                <div className="main-content">
                  <Header />
                  <div className="page-body">
                    <Routes>
                      <Route path="/dashboard"     element={<DashboardPage />} />
                      <Route path="/organizations" element={<OrganizationsPage />} />
                      <Route path="/projects"      element={<ProjectsPage />} />
                      <Route path="/queues"        element={<QueuesPage />} />
                      <Route path="/jobs"          element={<JobsPage />} />
                      <Route path="/jobs/:jobId"   element={<JobDetailPage />} />
                      <Route path="/workers"       element={<WorkersPage />} />
                      <Route path="/dlq"           element={<DeadLetterQueuePage />} />
                      <Route path="/metrics"       element={<MetricsPage />} />
                      <Route path="/"              element={<Navigate to="/dashboard" replace />} />
                    </Routes>
                  </div>
                </div>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

