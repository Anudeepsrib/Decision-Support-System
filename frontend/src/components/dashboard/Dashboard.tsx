import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Link } from 'react-router-dom';

export function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-2">
          Welcome, {user?.full_name}
        </h2>
        <p className="text-gray-600">
          You are logged in as <strong>{user?.role}</strong> with access to: {user?.sbu_access.join(', ')}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/upload"
          className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold mb-2">📄 Upload Documents</h3>
          <p className="text-sm text-gray-600">
            Upload PDF petitions and audited financials for AI extraction
          </p>
        </Link>

        <Link
          to="/mapping"
          className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold mb-2">✅ Mapping Workbench</h3>
          <p className="text-sm text-gray-600">
            Review and verify AI-suggested data mappings
          </p>
        </Link>

        <Link
          to="/reports"
          className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold mb-2">📊 Generate Reports</h3>
          <p className="text-sm text-gray-600">
            Create analytical reports and view audit trails
          </p>
        </Link>
      </div>

      <div className="bg-blue-50 p-4 rounded-lg">
        <h3 className="font-semibold mb-2">System Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            <span>Rule Engine: Active</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            <span>AI Extraction: Ready</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            <span>Audit Trail: Recording</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            <span>Security: Enabled</span>
          </div>
        </div>
      </div>
    </div>
  );
}
