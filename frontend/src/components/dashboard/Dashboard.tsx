import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Link } from 'react-router-dom';
import { HistoricalTrends } from './HistoricalTrends';
import { EfficiencyAnalysis } from './EfficiencyAnalysis';

export function Dashboard() {
  const { user } = useAuth();

  const quickLinks = [
    {
      path: '/upload',
      icon: '📄',
      title: 'Upload Documents',
      desc: 'Upload PDF petitions and audited financials for AI extraction',
      color: '#3182ce',
    },
    {
      path: '/mapping',
      icon: '🔗',
      title: 'Mapping Workbench',
      desc: 'Review and verify AI-suggested data mappings',
      color: '#38a169',
    },
    {
      path: '/reports',
      icon: '📈',
      title: 'Generate Reports',
      desc: 'Create analytical reports and view audit trails',
      color: '#d69e2e',
    },
  ];

  const statusItems = [
    { label: 'Rule Engine', status: 'Active' },
    { label: 'AI Extraction', status: 'Ready' },
    { label: 'Audit Trail', status: 'Recording' },
    { label: 'Security', status: 'Enabled' },
  ];

  return (
    <div>
      {/* Welcome Card */}
      <div style={styles.welcomeCard}>
        <h2 style={styles.welcomeTitle}>Welcome, {user?.full_name}</h2>
        <p style={styles.welcomeText}>
          You are logged in as <strong>{user?.role}</strong> with access to: {user?.sbu_access?.join(', ')}
        </p>
      </div>

      {/* Quick Links */}
      <div style={styles.cardsGrid}>
        {quickLinks.map((link) => (
          <Link key={link.path} to={link.path} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={{ fontSize: '1.5rem' }}>{link.icon}</span>
              <h3 style={{ ...styles.cardTitle, color: link.color }}>{link.title}</h3>
            </div>
            <p style={styles.cardDesc}>{link.desc}</p>
            <span style={{ ...styles.cardArrow, color: link.color }}>Open →</span>
          </Link>
        ))}
      </div>

      {/* System Status */}
      <div style={styles.statusCard}>
        <h3 style={styles.statusTitle}>System Status</h3>
        <div style={styles.statusGrid}>
          {statusItems.map((item) => (
            <div key={item.label} style={styles.statusItem}>
              <span style={styles.statusDot} />
              <span style={styles.statusLabel}>{item.label}: {item.status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Historical Trends */}
      <HistoricalTrends />

      {/* Efficiency Analysis */}
      <EfficiencyAnalysis />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  welcomeCard: {
    background: '#fff',
    padding: '1.5rem',
    borderRadius: '12px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    marginBottom: '1.5rem',
    borderLeft: '4px solid #3182ce',
  },
  welcomeTitle: {
    fontSize: '1.25rem',
    fontWeight: 600,
    color: '#1a365d',
    margin: '0 0 0.5rem',
  },
  welcomeText: {
    fontSize: '0.9rem',
    color: '#718096',
    margin: 0,
  },
  cardsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '1rem',
    marginBottom: '1.5rem',
  },
  card: {
    background: '#fff',
    padding: '1.25rem',
    borderRadius: '12px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    textDecoration: 'none',
    color: 'inherit',
    transition: 'all 0.2s ease',
    display: 'block',
    border: '1px solid #edf2f7',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '0.5rem',
  },
  cardTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    margin: 0,
  },
  cardDesc: {
    fontSize: '0.82rem',
    color: '#718096',
    margin: '0 0 0.75rem',
    lineHeight: 1.5,
  },
  cardArrow: {
    fontSize: '0.8rem',
    fontWeight: 600,
  },
  statusCard: {
    background: '#ebf8ff',
    padding: '1.25rem',
    borderRadius: '12px',
    marginBottom: '1.5rem',
    border: '1px solid #bee3f8',
  },
  statusTitle: {
    fontSize: '0.95rem',
    fontWeight: 600,
    color: '#2c5282',
    margin: '0 0 0.75rem',
  },
  statusGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '0.75rem',
  },
  statusItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: '#38a169',
    flexShrink: 0,
  },
  statusLabel: {
    fontSize: '0.82rem',
    color: '#2d3748',
  },
};
