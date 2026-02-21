import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard' },
    { path: '/upload', label: 'Upload PDF' },
    { path: '/mapping', label: 'Mapping Workbench' },
    { path: '/reports', label: 'Reports' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-blue-600 text-white shadow">
        <div className="container mx-auto px-4 py-3 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">ARR Truing-Up DSS</h1>
            <p className="text-xs opacity-75">KSERC MYT 2022-27 Framework</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm">{user?.full_name}</span>
            <span className="text-xs bg-blue-700 px-2 py-1 rounded">{user?.role}</span>
            <button
              onClick={logout}
              className="text-sm bg-blue-700 hover:bg-blue-800 px-3 py-1 rounded"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4">
          <div className="flex gap-6">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`py-3 border-b-2 transition-colors ${
                  location.pathname === item.path
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  );
}
