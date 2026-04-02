import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Login } from './components/auth/Login';
import { Layout } from './components/layout/Layout';

// Route-level code splitting
const Dashboard = React.lazy(() => import('./components/dashboard/Dashboard').then(module => ({ default: module.Dashboard })));
const OrderComparison = React.lazy(() => import('./components/comparison/OrderComparison').then(module => ({ default: module.OrderComparison })));
const ManualDecisions = React.lazy(() => import('./components/decisions/ManualDecisions').then(module => ({ default: module.ManualDecisions })));
const MappingWorkbench = React.lazy(() => import('./components/mapping/MappingWorkbench').then(module => ({ default: module.MappingWorkbench })));
const PDFUploader = React.lazy(() => import('./components/extraction/PDFUploader').then(module => ({ default: module.PDFUploader })));
const ReportDashboard = React.lazy(() => import('./components/reports/ReportDashboard').then(module => ({ default: module.ReportDashboard })));

// Wrapper to provide onUploadComplete callback
function UploadPage() {
  const navigate = React.useCallback(() => {}, []);
  return <PDFUploader onUploadComplete={() => {}} />;
}

function App() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <ErrorBoundary>
      <Layout>
        <Suspense fallback={<div className="flex items-center justify-center p-8">Loading view...</div>}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/compare" element={<OrderComparison />} />
            <Route path="/decisions" element={<ManualDecisions />} />
            <Route path="/mapping" element={<MappingWorkbench />} />
            <Route path="/reports" element={<ReportDashboard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </Layout>
    </ErrorBoundary>
  );
}

export default App;

