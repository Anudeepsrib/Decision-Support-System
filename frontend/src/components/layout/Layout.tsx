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
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/upload', label: 'Upload PDF', icon: '📄' },
    { path: '/mapping', label: 'Mapping Workbench', icon: '🔗' },
    { path: '/reports', label: 'Reports', icon: '📈' },
  ];

  return (
    <div style={styles.wrapper}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={styles.brandGroup}>
            <div style={styles.logoBox}>
              <svg width="32" height="32" viewBox="0 0 40 40" fill="none">
                <rect width="40" height="40" rx="10" fill="rgba(255,255,255,0.15)" />
                <path d="M12 28V14l8-4 8 4v14l-8 4-8-4z" stroke="#fff" strokeWidth="2" fill="none" />
                <path d="M20 10v22M12 14l8 4 8-4M12 28l8-4 8 4" stroke="#fff" strokeWidth="1.5" opacity="0.5" />
              </svg>
            </div>
            <div>
              <h1 style={styles.headerTitle}>ARR Truing-Up DSS</h1>
              <p style={styles.headerSub}>KSERC MYT 2022-27 Framework</p>
            </div>
          </div>
          <div style={styles.userSection}>
            <div style={styles.userInfo}>
              <span style={styles.userName}>{user?.full_name}</span>
              <span style={styles.userRole}>{user?.role}</span>
            </div>
            <button
              onClick={logout}
              style={styles.logoutBtn}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.25)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; }}
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav style={styles.nav}>
        <div style={styles.navInner}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  ...styles.navLink,
                  ...(isActive ? styles.navLinkActive : {}),
                }}
              >
                <span style={{ marginRight: '0.4rem' }}>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Main Content */}
      <main style={styles.main}>
        <div style={styles.contentWrapper}>
          {children}
        </div>
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    minHeight: '100vh',
    background: '#f0f4f8',
    fontFamily: "'Roboto', 'Noto Sans Malayalam', sans-serif",
  },
  header: {
    background: 'linear-gradient(135deg, #1a365d 0%, #2c5282 100%)',
    color: '#fff',
    boxShadow: '0 2px 12px rgba(26, 54, 93, 0.3)',
  },
  headerInner: {
    maxWidth: '1280px',
    margin: '0 auto',
    padding: '0.75rem 1.5rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  brandGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  logoBox: {
    display: 'flex',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: '1.15rem',
    fontWeight: 700,
    margin: 0,
    letterSpacing: '-0.01em',
  },
  headerSub: {
    fontSize: '0.7rem',
    margin: 0,
    opacity: 0.7,
    letterSpacing: '0.02em',
  },
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'flex-end',
  },
  userName: {
    fontSize: '0.85rem',
    fontWeight: 500,
  },
  userRole: {
    fontSize: '0.65rem',
    background: 'rgba(255,255,255,0.15)',
    padding: '0.15rem 0.5rem',
    borderRadius: '10px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  },
  logoutBtn: {
    fontSize: '0.8rem',
    background: 'rgba(255,255,255,0.1)',
    color: '#fff',
    border: '1px solid rgba(255,255,255,0.2)',
    padding: '0.4rem 1rem',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    fontFamily: 'inherit',
    fontWeight: 500,
  },
  nav: {
    background: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
  },
  navInner: {
    maxWidth: '1280px',
    margin: '0 auto',
    padding: '0 1.5rem',
    display: 'flex',
    gap: '0.25rem',
  },
  navLink: {
    padding: '0.75rem 1rem',
    fontSize: '0.85rem',
    fontWeight: 500,
    color: '#718096',
    textDecoration: 'none',
    borderBottom: '2px solid transparent',
    transition: 'all 0.2s ease',
  },
  navLinkActive: {
    color: '#2c5282',
    borderBottom: '2px solid #3182ce',
    fontWeight: 600,
  },
  main: {
    padding: '1.5rem',
  },
  contentWrapper: {
    maxWidth: '1280px',
    margin: '0 auto',
  },
};
