import React, { useState } from 'react';
import { ReportsService } from '../../services/api';
import { AnalyticalReport, SBUCode } from '../../services/types';
import { toast } from 'react-toastify';
import { TariffDraft } from './TariffDraft';

export function ReportDashboard() {
  const [report, setReport] = useState<AnalyticalReport | null>(null);
  const [financialYear, setFinancialYear] = useState('2024-25');
  const [selectedSBU, setSelectedSBU] = useState<SBUCode | ''>('');
  const [loading, setLoading] = useState(false);

  const generateReport = async () => {
    setLoading(true);
    setReport(null);
    try {
      const data = await ReportsService.generateAnalyticalReport(financialYear, selectedSBU || undefined);
      setReport(data);
      toast.success('✅ Report generated successfully');
    } catch {
      toast.error('Failed to generate report. Ensure mappings have been confirmed first.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="slideUp">
      <div style={s.pageHeader}>
        <h2 style={s.pageTitle}>Analytical Reports</h2>
        <p style={s.pageDesc}>Generate a full variance analysis with AI-driven regulatory insights.</p>
      </div>

      {/* ── Controls ── */}
      <div style={s.controlsCard}>
        <div style={s.controlsRow}>
          <div style={s.controlGroup}>
            <label style={s.label}>Financial Year</label>
            <select value={financialYear} onChange={(e) => setFinancialYear(e.target.value)} style={s.select}>
              {['2022-23', '2023-24', '2024-25', '2025-26', '2026-27'].map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <div style={s.controlGroup}>
            <label style={s.label}>SBU (Optional)</label>
            <select value={selectedSBU} onChange={(e) => setSelectedSBU(e.target.value as SBUCode | '')} style={s.select}>
              <option value="">All SBUs</option>
              <option value={SBUCode.SBU_GENERATION}>Generation (SBU-G)</option>
              <option value={SBUCode.SBU_TRANSMISSION}>Transmission (SBU-T)</option>
              <option value={SBUCode.SBU_DISTRIBUTION}>Distribution (SBU-D)</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              onClick={generateReport}
              disabled={loading}
              style={{ ...s.generateBtn, ...(loading ? s.generateBtnLoading : {}) }}
              onMouseEnter={(e) => { if (!loading) { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(44,82,130,0.4)'; } }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 3px 12px rgba(44,82,130,0.3)'; }}
            >
              {loading ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={s.btnSpinner} /> Generating...
                </span>
              ) : '📊 Generate Report'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Skeleton Loading ── */}
      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={s.skeletonGrid}>
            {[1, 2, 3, 4].map(i => (
              <div key={i} style={s.skeletonCard}>
                <div className="skeleton" style={s.skeletonLabel} />
                <div className="skeleton" style={s.skeletonValue} />
              </div>
            ))}
          </div>
          <div className="skeleton" style={s.skeletonBlock} />
          <div className="skeleton" style={{ ...s.skeletonBlock, height: '100px' }} />
        </div>
      )}

      {/* ── Report Output ── */}
      {report && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '1.25rem' }} className="slideUp">

          {/* KPI Summary Cards */}
          <div style={s.summaryGrid}>
            <KpiCard
              label="Approved ARR"
              value={`₹${(report.preliminary_summary.total_approved_arr / 1e7).toFixed(2)} Cr`}
              sub={financialYear}
              accentColor="#2c5282"
              icon="✅"
            />
            <KpiCard
              label="Actual ARR"
              value={`₹${(report.preliminary_summary.total_actual_arr / 1e7).toFixed(2)} Cr`}
              sub={financialYear}
              accentColor="#3182ce"
              icon="📊"
            />
            <KpiCard
              label="Net Variance"
              value={`₹${(report.preliminary_summary.net_variance / 1e7).toFixed(2)} Cr`}
              sub={report.preliminary_summary.net_variance < 0 ? 'Shortfall' : 'Surplus'}
              accentColor={report.preliminary_summary.net_variance < 0 ? '#c53030' : '#276749'}
              icon={report.preliminary_summary.net_variance < 0 ? '📉' : '📈'}
            />
            <KpiCard
              label="Anomalies"
              value={String(report.anomaly_count)}
              sub={report.anomaly_count > 0 ? 'Requires review' : 'All clear'}
              accentColor={report.anomaly_count > 0 ? '#b45309' : '#276749'}
              icon={report.anomaly_count > 0 ? '⚠️' : '✅'}
            />
          </div>

          {/* AI Insights */}
          {report.insights.length > 0 && (
            <div style={s.insightBox}>
              <h3 style={s.sectionTitle}>💡 AI Insights</h3>
              <div style={s.insightList}>
                {report.insights.map((insight, idx) => (
                  <div key={idx} style={s.insightRow} className="slideUp">
                    <span style={s.insightDot} />
                    <span style={s.insightText}>{insight}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Regulatory Recommendations */}
          {report.recommendations.length > 0 && (
            <div style={s.recoBox}>
              <h3 style={s.sectionTitle}>🔍 Regulatory Recommendations</h3>
              <div style={s.insightList}>
                {report.recommendations.map((rec, idx) => (
                  <div key={idx} style={{ ...s.insightRow, borderLeftColor: '#f6e05e' }} className="slideUp">
                    <span style={{ ...s.insightDot, background: '#d69e2e' }} />
                    <span style={s.insightText}>{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cost Head Breakdown */}
          {report.cost_head_breakdown && Object.keys(report.cost_head_breakdown).length > 0 && (
            <div style={s.breakdownCard}>
              <h3 style={s.sectionTitle}>📋 Cost Head Breakdown</h3>
              <div style={s.breakdownTable}>
                <div style={s.breakdownHeader}>
                  <span>Cost Head</span><span>Approved</span><span>Actual</span><span>Variance</span>
                </div>
                {Object.entries(report.cost_head_breakdown).map(([head, data], idx) => {
                  const variance = data.variance;
                  const isNeg = variance < 0;
                  return (
                    <div key={head} style={{ ...s.breakdownRow, background: idx % 2 ? '#f8fafc' : '#fff' }}>
                      <span style={s.breakdownHead}>{head.replace(/_/g, ' ')}</span>
                      <span style={s.breakdownNum}>₹{(data.approved / 1e7).toFixed(2)} Cr</span>
                      <span style={s.breakdownNum}>₹{(data.actual / 1e7).toFixed(2)} Cr</span>
                      <span style={{ ...s.breakdownNum, color: isNeg ? '#c53030' : '#276749', fontWeight: 700 }}>
                        {isNeg ? '▼' : '▲'} ₹{Math.abs(variance / 1e7).toFixed(2)} Cr
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tariff Draft */}
          <TariffDraft report={report} />

          {/* Metadata footer */}
          <div style={s.metadata}>
            <span>Report ID: <code style={{ fontFamily: 'JetBrains Mono, monospace' }}>{report.report_id}</code></span>
            <span>·</span>
            <span>Checksum: <code style={{ fontFamily: 'JetBrains Mono, monospace' }}>{report.checksum.substring(0, 16)}…</code></span>
            <span>·</span>
            <span>Generated: {new Date(report.generated_at).toLocaleString('en-IN')}</span>
          </div>
        </div>
      )}

      {/* ── Empty State ── */}
      {!loading && !report && (
        <div style={s.emptyState}>
          <span style={{ fontSize: '3rem' }}>📊</span>
          <p style={s.emptyTitle}>No report generated yet</p>
          <p style={s.emptyDesc}>
            Select a financial year and click "Generate Report" to see variance analysis and AI-driven insights.
          </p>
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value, sub, accentColor, icon }: {
  label: string; value: string; sub: string; accentColor: string; icon: string;
}) {
  return (
    <div style={{ ...kpi.card, borderTop: `4px solid ${accentColor}` }}>
      <div style={kpi.top}>
        <p style={kpi.label}>{label}</p>
        <span style={{ fontSize: '1.3rem' }}>{icon}</span>
      </div>
      <p style={{ ...kpi.value, color: accentColor }}>{value}</p>
      <p style={kpi.sub}>{sub}</p>
    </div>
  );
}

const kpi: Record<string, React.CSSProperties> = {
  card: {
    background: '#fff', borderRadius: '16px', padding: '1.25rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #e2e8f0',
    display: 'flex', flexDirection: 'column' as const,
  },
  top: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' },
  label: { fontSize: '0.72rem', color: '#a0aec0', margin: 0, textTransform: 'uppercase' as const, letterSpacing: '0.06em', fontWeight: 700 },
  value: { fontSize: '1.75rem', fontWeight: 900, margin: '0 0 0.15rem', lineHeight: 1.1 },
  sub: { fontSize: '0.72rem', color: '#a0aec0', margin: 0, fontWeight: 500 },
};

const s: Record<string, React.CSSProperties> = {
  pageHeader: { marginBottom: '1.25rem' },
  pageTitle: { fontSize: '1.4rem', fontWeight: 800, color: '#1a202c', margin: '0 0 0.3rem' },
  pageDesc: { fontSize: '0.85rem', color: '#718096', margin: 0 },

  // Controls
  controlsCard: {
    background: '#fff', borderRadius: '16px', padding: '1.25rem 1.5rem',
    boxShadow: '0 1px 6px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0', marginBottom: '1.5rem',
  },
  controlsRow: { display: 'flex', gap: '1rem', flexWrap: 'wrap' as const, alignItems: 'flex-end' },
  controlGroup: { display: 'flex', flexDirection: 'column' as const },
  label: { fontSize: '0.75rem', fontWeight: 700, color: '#4a5568', marginBottom: '0.3rem', letterSpacing: '0.03em' },
  select: {
    padding: '0.55rem 0.8rem', border: '1.5px solid #e2e8f0', borderRadius: '8px',
    fontSize: '0.85rem', background: '#f8fafc', fontFamily: 'Inter, sans-serif',
    outline: 'none', minWidth: '160px', cursor: 'pointer',
  },
  generateBtn: {
    padding: '0.6rem 1.35rem',
    background: 'linear-gradient(135deg, #1e3a6e 0%, #2c5282 50%, #3182ce 100%)',
    color: '#fff', border: 'none', borderRadius: '10px', fontWeight: 700,
    fontSize: '0.88rem', cursor: 'pointer', fontFamily: 'inherit',
    boxShadow: '0 3px 12px rgba(44,82,130,0.3)', transition: 'all 0.2s ease',
    whiteSpace: 'nowrap' as const,
  },
  generateBtnLoading: { opacity: 0.7, cursor: 'not-allowed' },
  btnSpinner: {
    display: 'inline-block', width: '14px', height: '14px',
    border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff',
    borderRadius: '50%', animation: 'spin 0.8s linear infinite',
  },

  // Skeletons
  skeletonGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' },
  skeletonCard: { background: '#fff', borderRadius: '16px', padding: '1.25rem', border: '1px solid #e2e8f0' },
  skeletonLabel: { height: '12px', width: '60%', marginBottom: '0.75rem' },
  skeletonValue: { height: '28px', width: '45%' },
  skeletonBlock: { borderRadius: '16px', height: '140px' },

  // KPI grid
  summaryGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' },

  // Insights
  insightBox: {
    background: 'linear-gradient(135deg, #ebf8ff 0%, #e6fffa 100%)',
    padding: '1.5rem', borderRadius: '16px', border: '1.5px solid #bee3f8',
  },
  recoBox: {
    background: 'linear-gradient(135deg, #fffff0 0%, #fefce8 100%)',
    padding: '1.5rem', borderRadius: '16px', border: '1.5px solid #fef08a',
  },
  sectionTitle: { fontSize: '0.95rem', fontWeight: 800, color: '#1a202c', margin: '0 0 1rem' },
  insightList: { display: 'flex', flexDirection: 'column' as const, gap: '0.6rem' },
  insightRow: { display: 'flex', gap: '0.75rem', borderLeft: '3px solid #63b3ed', paddingLeft: '0.75rem', alignItems: 'flex-start' },
  insightDot: { display: 'none' },
  insightText: { fontSize: '0.84rem', color: '#2d3748', lineHeight: 1.6 },

  // Cost head breakdown
  breakdownCard: {
    background: '#fff', borderRadius: '16px', padding: '1.5rem',
    boxShadow: '0 1px 6px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0',
  },
  breakdownTable: { borderRadius: '10px', overflow: 'hidden', border: '1px solid #e2e8f0' },
  breakdownHeader: {
    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr',
    padding: '0.6rem 1rem', background: '#f7fafc',
    fontSize: '0.72rem', fontWeight: 700, color: '#718096',
    textTransform: 'uppercase' as const, letterSpacing: '0.05em',
    borderBottom: '1px solid #e2e8f0',
  },
  breakdownRow: {
    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr',
    padding: '0.65rem 1rem', borderBottom: '1px solid #f0f4f8',
  },
  breakdownHead: { fontSize: '0.83rem', fontWeight: 600, color: '#2d3748' },
  breakdownNum: { fontSize: '0.83rem', color: '#4a5568' },

  // Empty state
  emptyState: {
    background: '#fff', borderRadius: '20px', padding: '4rem 2rem',
    textAlign: 'center' as const, border: '1px solid #e2e8f0',
    display: 'flex', flexDirection: 'column' as const, alignItems: 'center', gap: '0.5rem',
  },
  emptyTitle: { fontSize: '1.1rem', fontWeight: 700, color: '#2d3748', margin: 0 },
  emptyDesc: { fontSize: '0.84rem', color: '#a0aec0', margin: 0, maxWidth: '400px', lineHeight: 1.6 },

  // Footer
  metadata: {
    fontSize: '0.72rem', color: '#a0aec0', textAlign: 'center' as const,
    padding: '0.5rem 0', display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap' as const,
  },
};
