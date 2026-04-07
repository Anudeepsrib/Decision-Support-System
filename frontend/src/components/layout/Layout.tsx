import React, { useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import DemoModeBanner from '../common/DemoModeBanner';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const mainRef = useRef<HTMLDivElement>(null);

  // Fade-in on route change
  useEffect(() => {
    if (mainRef.current) {
      mainRef.current.style.opacity = '0';
      mainRef.current.style.transform = 'translateY(8px)';
      const t = setTimeout(() => {
        if (mainRef.current) {
          mainRef.current.style.opacity = '1';
          mainRef.current.style.transform = 'translateY(0)';
        }
      }, 30);
      return () => clearTimeout(t);
    }
  }, [location.pathname]);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/compare', label: 'Order Compare', icon: '�' },
    { path: '/mapping', label: 'Mapping Workbench', icon: '🔗' },
    { path: '/decisions', label: 'Manual Decisions', icon: '✓' },
  ];

  const roleColor: Record<string, string> = {
    super_admin: 'rgba(99,179,237,0.25)',
    regulatory_officer: 'rgba(154,230,180,0.25)',
    senior_auditor: 'rgba(251,211,141,0.25)',
    data_entry_agent: 'rgba(190,227,248,0.25)',
    readonly_analyst: 'rgba(214,188,250,0.25)',
  };

  const roleBg = roleColor[user?.role || ''] || 'rgba(255,255,255,0.15)';

  return (
    <div style={s.wrapper}>
      {/* Demo Mode Banner */}
      <DemoModeBanner />
      
      {/* ─── Header ─── */}
      <header style={s.header}>
        <div style={s.headerInner}>
          {/* Brand */}
          <div style={s.brand}>
            <div style={s.logoWrap}>
              <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
                <rect width="40" height="40" rx="10" fill="rgba(255,255,255,0.12)" />
                <path d="M12 28V14l8-4 8 4v14l-8 4-8-4z" stroke="#93c5fd" strokeWidth="2" fill="none" />
                <path d="M20 10v22M12 14l8 4 8-4M12 28l8-4 8 4" stroke="#93c5fd" strokeWidth="1.5" opacity="0.5" />
              </svg>
            </div>
            <div>
              <h1 style={s.headerTitle}>ARR Truing-Up DSS</h1>
              <p style={s.headerSub}>KSERC MYT 2022-27 Framework</p>
            </div>
          </div>

          {/* Status chip */}
          <div style={s.statusChip}>
            <span className="pulse-dot" />
            <span style={s.statusLabel}>Live</span>
          </div>

          {/* User */}
          <div style={s.userSection}>
            <div style={s.userCard}>
              <span style={s.userName}>{user?.full_name}</span>
              <span style={{ ...s.roleBadge, background: roleBg }}>
                {(user?.role || '').replace('_', ' ').toUpperCase()}
              </span>
            </div>
            <button
              onClick={logout}
              style={s.logoutBtn}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; }}
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* ─── Navigation ─── */}
      <nav style={s.nav}>
        <div style={s.navInner}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{ ...s.navLink, ...(isActive ? s.navLinkActive : {}) }}
                onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.color = '#2c5282'; }}
                onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.color = '#718096'; }}
              >
                <span style={s.navIcon}>{item.icon}</span>
                <span>{item.label}</span>
                {isActive && <span style={s.activePill} />}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* ─── Main Content ─── */}
      <main style={s.main}>
        <div
          ref={mainRef}
          style={{ ...s.contentWrapper, transition: 'opacity 0.25s ease, transform 0.25s ease' }}
        >
          {children}
        </div>
      </main>

      {/* ─── Footer ─── */}
      <footer style={s.footer}>
        <span>ARR Decision Support System · KSERC MYT 2022-27</span>
        <span>·</span>
        <span>v1.0.0</span>
      </footer>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  wrapper: {
    minHeight: '100vh',
    background: 'var(--surface-2, #f0f4f8)',
    fontFamily: "'Inter', sans-serif",
    display: 'flex',
    flexDirection: 'column',
  },

  // Header
  header: {
    background: 'linear-gradient(135deg, #0f1f3d 0%, #1e3a6e 50%, #2c5282 100%)',
    color: '#fff',
    boxShadow: '0 2px 20px rgba(15,31,61,0.4)',
    position: 'sticky' as const,
    top: 0,
    zIndex: 100,
  },
  headerInner: {
    maxWidth: '1360px',
    margin: '0 auto',
    padding: '0 1.5rem',
    height: '60px',
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    flex: '1 1 auto',
  },
  logoWrap: {
    background: 'rgba(255,255,255,0.1)',
    borderRadius: '10px',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: '1rem',
    fontWeight: 800,
    margin: 0,
    letterSpacing: '-0.02em',
    color: '#fff',
  },
  headerSub: {
    fontSize: '0.65rem',
    margin: 0,
    opacity: 0.6,
    letterSpacing: '0.04em',
    textTransform: 'uppercase' as const,
  },

  // Live status
  statusChip: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
    background: 'rgba(56,161,105,0.15)',
    border: '1px solid rgba(56,161,105,0.3)',
    borderRadius: '999px',
    padding: '0.2rem 0.7rem',
  },
  statusLabel: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#68d391',
    letterSpacing: '0.08em',
    textTransform: 'uppercase' as const,
  },

  // User section
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    flexShrink: 0,
  },
  userCard: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'flex-end',
    gap: '0.15rem',
  },
  userName: {
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#fff',
  },
  roleBadge: {
    fontSize: '0.58rem',
    padding: '0.15rem 0.5rem',
    borderRadius: '999px',
    letterSpacing: '0.08em',
    fontWeight: 700,
    color: '#fff',
    border: '1px solid rgba(255,255,255,0.2)',
  },
  logoutBtn: {
    fontSize: '0.78rem',
    background: 'rgba(255,255,255,0.08)',
    color: '#fff',
    border: '1px solid rgba(255,255,255,0.2)',
    padding: '0.35rem 0.85rem',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    fontFamily: 'inherit',
    fontWeight: 600,
    letterSpacing: '0.02em',
  },

  // Navigation
  nav: {
    background: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
  },
  navInner: {
    maxWidth: '1360px',
    margin: '0 auto',
    padding: '0 1.5rem',
    display: 'flex',
    gap: '0.1rem',
  },
  navLink: {
    position: 'relative' as const,
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    padding: '0.85rem 1rem',
    fontSize: '0.83rem',
    fontWeight: 500,
    color: '#718096',
    textDecoration: 'none',
    transition: 'color 0.2s ease',
    whiteSpace: 'nowrap' as const,
  },
  navLinkActive: {
    color: '#2c5282',
    fontWeight: 700,
  },
  navIcon: {
    fontSize: '0.95rem',
    lineHeight: 1,
  },
  activePill: {
    position: 'absolute' as const,
    bottom: 0,
    left: '0.5rem',
    right: '0.5rem',
    height: '3px',
    background: 'linear-gradient(90deg, #2c5282, #3182ce)',
    borderRadius: '3px 3px 0 0',
  },

  // Main
  main: {
    flex: 1,
    padding: '1.5rem',
  },
  contentWrapper: {
    maxWidth: '1360px',
    margin: '0 auto',
  },

  // Footer
  footer: {
    display: 'flex',
    gap: '0.5rem',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '0.75rem 1rem',
    fontSize: '0.68rem',
    color: '#a0aec0',
    borderTop: '1px solid #e2e8f0',
    background: '#fff',
  },
};
