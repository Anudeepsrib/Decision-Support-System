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
      icon: '📤',
      title: 'Upload Documents',
      desc: 'Upload PDF petitions and audited financials for AI extraction',
      gradient: 'linear-gradient(135deg, #2c5282 0%, #3182ce 100%)',
      glow: 'rgba(49,130,206,0.2)',
    },
    {
      path: '/mapping',
      icon: '🔗',
      title: 'Mapping Workbench',
      desc: 'Review and verify AI-suggested data mappings before they reach the rule engine',
      gradient: 'linear-gradient(135deg, #276749 0%, #38a169 100%)',
      glow: 'rgba(56,161,105,0.2)',
    },
    {
      path: '/reports',
      icon: '📈',
      title: 'Generate Reports',
      desc: 'Create analytical reports, view variance breakdowns and audit trails',
      gradient: 'linear-gradient(135deg, #744210 0%, #d69e2e 100%)',
      glow: 'rgba(214,158,46,0.2)',
    },
  ];

  const statusItems = [
    { label: 'Rule Engine', status: 'Active', color: '#38a169' },
    { label: 'AI Extraction', status: 'Ready', color: '#38a169' },
    { label: 'Audit Trail', status: 'Recording', color: '#d69e2e' },
    { label: 'Security', status: 'Enforced', color: '#3182ce' },
  ];

  return (
    <div className="slideUp">
      {/* ── Welcome Card ── */}
      <div style={s.welcomeCard}>
        <div style={s.welcomeLeft}>
          <div style={s.welcomeAvatar}>
            {(user?.full_name?.charAt(0) || 'U').toUpperCase()}
          </div>
          <div>
            <h2 style={s.welcomeTitle}>Welcome back, {user?.full_name?.split(' ')[0]}!</h2>
            <p style={s.welcomeDesc}>
              Logged in as <strong>{(user?.role || '').replace(/_/g, ' ')}</strong>
              {user?.sbu_access && user.sbu_access.length > 0 &&
                <> · Access: {user.sbu_access.map(sbu => (
                  <span key={sbu} style={s.sbuChip}>{sbu}</span>
                ))}</>
              }
            </p>
          </div>
        </div>
        <div style={s.dateChip}>
          📅 {new Date().toLocaleDateString('en-IN', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
        </div>
      </div>

      {/* ── Quick Action Cards ── */}
      <div style={s.cardsGrid}>
        {quickLinks.map((link) => (
          <Link
            key={link.path}
            to={link.path}
            style={s.card}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)';
              e.currentTarget.style.boxShadow = `0 12px 40px ${link.glow}, 0 4px 16px rgba(0,0,0,0.08)`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)';
            }}
          >
            <div style={{ ...s.cardIconWrap, background: link.gradient }}>
              <span style={s.cardIcon}>{link.icon}</span>
            </div>
            <h3 style={s.cardTitle}>{link.title}</h3>
            <p style={s.cardDesc}>{link.desc}</p>
            <span style={s.cardArrow}>Open →</span>
          </Link>
        ))}
      </div>

      {/* ── System Status ── */}
      <div style={s.statusCard}>
        <h3 style={s.statusTitle}>⚙️ System Status</h3>
        <div style={s.statusGrid}>
          {statusItems.map((item) => (
            <div key={item.label} style={s.statusItem}>
              <span
                className="pulse-dot"
                style={{ background: item.color, boxShadow: `0 0 0 3px ${item.color}33` }}
              />
              <div>
                <span style={s.statusItemLabel}>{item.label}</span>
                <span style={{ ...s.statusItemValue, color: item.color }}>{item.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Workflow Guide ── */}
      <div style={s.workflowCard}>
        <h3 style={s.workflowTitle}>📋 Workflow Guide</h3>
        <div style={s.workflowSteps}>
          {[
            { n: '1', icon: '📤', title: 'Upload PDF', desc: 'Drag & drop or browse your PDF petition / audited financials' },
            { n: '2', icon: '🤖', title: 'AI Extraction', desc: 'System extracts all financial tables with confidence scores' },
            { n: '3', icon: '✍️', title: 'Review Mappings', desc: 'Confirm or override AI-suggested regulatory classifications' },
            { n: '4', icon: '📊', title: 'Generate Report', desc: 'Get a full analytical report with variance and compliance insights' },
          ].map((step, idx) => (
            <div key={idx} style={s.wfStep}>
              <div style={s.wfNum}>{step.n}</div>
              {idx < 3 && <div style={s.wfConnector} />}
              <div style={s.wfIcon}>{step.icon}</div>
              <p style={s.wfTitle}>{step.title}</p>
              <p style={s.wfDesc}>{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Analytics sections */}
      <HistoricalTrends />
      <EfficiencyAnalysis />
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  // Welcome
  welcomeCard: {
    background: 'linear-gradient(135deg, #0f1f3d 0%, #1e3a6e 60%, #2c5282 100%)',
    color: '#fff', borderRadius: '20px', padding: '1.5rem 1.75rem',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: '1.5rem', boxShadow: '0 8px 32px rgba(15,31,61,0.25)',
    flexWrap: 'wrap' as const, gap: '1rem',
  },
  welcomeLeft: { display: 'flex', alignItems: 'center', gap: '1rem' },
  welcomeAvatar: {
    width: '48px', height: '48px', borderRadius: '50%',
    background: 'rgba(255,255,255,0.15)', border: '2px solid rgba(255,255,255,0.3)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: '1.2rem', fontWeight: 800, color: '#fff', flexShrink: 0,
  },
  welcomeTitle: { fontSize: '1.15rem', fontWeight: 800, margin: '0 0 0.25rem', color: '#fff' },
  welcomeDesc: { fontSize: '0.82rem', margin: 0, opacity: 0.85, display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' as const },
  sbuChip: {
    background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.25)',
    borderRadius: '999px', padding: '0.1rem 0.5rem', fontSize: '0.72rem', fontWeight: 700,
  },
  dateChip: {
    fontSize: '0.78rem', background: 'rgba(255,255,255,0.1)',
    border: '1px solid rgba(255,255,255,0.2)', borderRadius: '10px',
    padding: '0.4rem 0.85rem', color: 'rgba(255,255,255,0.9)', flexShrink: 0,
  },

  // Quick link cards
  cardsGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))',
    gap: '1rem', marginBottom: '1.5rem',
  },
  card: {
    background: '#fff', padding: '1.5rem', borderRadius: '18px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)', textDecoration: 'none', color: 'inherit',
    transition: 'all 0.25s ease', display: 'flex', flexDirection: 'column' as const,
    border: '1px solid rgba(0,0,0,0.05)',
  },
  cardIconWrap: {
    width: '48px', height: '48px', borderRadius: '14px',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    marginBottom: '1rem', flexShrink: 0,
  },
  cardIcon: { fontSize: '1.4rem' },
  cardTitle: { fontSize: '1rem', fontWeight: 800, margin: '0 0 0.4rem', color: '#1a202c' },
  cardDesc: { fontSize: '0.8rem', color: '#718096', margin: '0 0 0.9rem', lineHeight: 1.55, flex: 1 },
  cardArrow: { fontSize: '0.8rem', fontWeight: 700, color: '#3182ce' },

  // System status
  statusCard: {
    background: '#fff', borderRadius: '16px', padding: '1.25rem 1.5rem',
    marginBottom: '1.5rem', border: '1px solid #e2e8f0',
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
  },
  statusTitle: { fontSize: '0.9rem', fontWeight: 700, color: '#2d3748', margin: '0 0 0.9rem' },
  statusGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem' },
  statusItem: { display: 'flex', alignItems: 'center', gap: '0.6rem' },
  statusItemLabel: { display: 'block', fontSize: '0.75rem', color: '#718096', fontWeight: 500 },
  statusItemValue: { display: 'block', fontSize: '0.72rem', fontWeight: 700 },

  // Workflow guide
  workflowCard: {
    background: '#fff', borderRadius: '16px', padding: '1.25rem 1.5rem',
    marginBottom: '1.5rem', border: '1px solid #e2e8f0',
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
  },
  workflowTitle: { fontSize: '0.9rem', fontWeight: 700, color: '#2d3748', margin: '0 0 1rem' },
  workflowSteps: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '1rem', position: 'relative' as const,
  },
  wfStep: { display: 'flex', flexDirection: 'column' as const, alignItems: 'flex-start', gap: '0.3rem', position: 'relative' as const },
  wfNum: {
    width: '22px', height: '22px', borderRadius: '50%',
    background: 'linear-gradient(135deg, #2c5282, #3182ce)', color: '#fff',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: '0.7rem', fontWeight: 800, flexShrink: 0, marginBottom: '0.25rem',
  },
  wfConnector: {},
  wfIcon: { fontSize: '1.3rem' },
  wfTitle: { fontSize: '0.85rem', fontWeight: 700, color: '#2d3748', margin: 0 },
  wfDesc: { fontSize: '0.76rem', color: '#a0aec0', margin: 0, lineHeight: 1.5 },
};
