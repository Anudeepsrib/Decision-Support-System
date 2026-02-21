import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { Login } from './components/auth/Login';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './components/dashboard/Dashboard';
import { PDFUploader } from './components/extraction/PDFUploader';
import { MappingWorkbench } from './components/mapping/MappingWorkbench';
import { ReportDashboard } from './components/reports/ReportDashboard';
import { ExtractionResponse } from './services/types';

function App() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/upload" element={<PDFUploader onUploadComplete={(r: ExtractionResponse) => console.log(r)} />} />
        <Route path="/mapping" element={<MappingWorkbench />} />
        <Route path="/reports" element={<ReportDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default App;
