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
    try {
      const data = await ReportsService.generateAnalyticalReport(financialYear, selectedSBU || undefined);
      setReport(data);
      toast.success('Report generated successfully');
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 style={s.pageTitle}>Analytical Reports</h2>

      {/* Controls */}
      <div style={s.controlsRow}>
        <div style={s.controlGroup}>
          <label style={s.label}>Financial Year</label>
          <select value={financialYear} onChange={(e) => setFinancialYear(e.target.value)} style={s.select}>
            <option value="2022-23">2022-23</option>
            <option value="2023-24">2023-24</option>
            <option value="2024-25">2024-25</option>
            <option value="2025-26">2025-26</option>
            <option value="2026-27">2026-27</option>
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
          <button onClick={generateReport} disabled={loading} style={{ ...s.generateBtn, ...(loading ? { opacity: 0.6 } : {}) }}>
            {loading ? 'Generating...' : '📊 Generate Report'}
          </button>
        </div>
      </div>

      {report && (
        <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '1.25rem' }}>
          {/* Summary Cards */}
          <div style={s.summaryGrid}>
            <SummaryCard label="Approved ARR" value={`₹${(report.preliminary_summary.total_approved_arr / 1e7).toFixed(2)} Cr`} color="#3182ce" />
            <SummaryCard label="Actual ARR" value={`₹${(report.preliminary_summary.total_actual_arr / 1e7).toFixed(2)} Cr`} color="#2c5282" />
            <SummaryCard
              label="Net Variance"
              value={`₹${(report.preliminary_summary.net_variance / 1e7).toFixed(2)} Cr`}
              color={report.preliminary_summary.net_variance < 0 ? '#e53e3e' : '#38a169'}
            />
            <SummaryCard label="Anomalies" value={String(report.anomaly_count)} color="#d69e2e" />
          </div>

          {/* AI Insights */}
          {report.insights.length > 0 && (
            <div style={s.insightBox}>
              <h3 style={s.sectionTitle}>💡 AI Insights</h3>
              <ul style={s.list}>
                {report.insights.map((insight, idx) => (
                  <li key={idx} style={s.listItem}>{insight}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {report.recommendations.length > 0 && (
            <div style={s.recoBox}>
              <h3 style={s.sectionTitle}>🔍 Regulatory Recommendations</h3>
              <ul style={s.list}>
                {report.recommendations.map((rec, idx) => (
                  <li key={idx} style={s.listItem}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Tariff Draft */}
          <TariffDraft report={report} />

          {/* Metadata */}
          <div style={s.metadata}>
            Report ID: {report.report_id} | Checksum: {report.checksum.substring(0, 16)}... | Generated: {new Date(report.generated_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={s.summaryCard}>
      <p style={s.summaryLabel}>{label}</p>
      <p style={{ ...s.summaryValue, color }}>{value}</p>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  pageTitle: { fontSize: '1.35rem', fontWeight: 600, color: '#1a365d', margin: '0 0 1.25rem' },
  controlsRow: {
    display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' as const,
    background: '#fff', padding: '1.25rem', borderRadius: '12px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)', border: '1px solid #edf2f7',
  },
  controlGroup: { display: 'flex', flexDirection: 'column' as const },
  label: { fontSize: '0.78rem', fontWeight: 600, color: '#4a5568', marginBottom: '0.3rem', letterSpacing: '0.02em' },
  select: {
    padding: '0.55rem 0.8rem', border: '1.5px solid #e2e8f0', borderRadius: '8px',
    fontSize: '0.85rem', background: '#f7fafc', fontFamily: 'inherit', outline: 'none', minWidth: '160px',
  },
  generateBtn: {
    padding: '0.55rem 1.25rem', background: 'linear-gradient(135deg, #2c5282 0%, #2b6cb0 100%)',
    color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 600, fontSize: '0.85rem',
    cursor: 'pointer', fontFamily: 'inherit', boxShadow: '0 2px 8px rgba(44,82,130,0.3)',
  },
  summaryGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' },
  summaryCard: {
    background: '#fff', padding: '1.25rem', borderRadius: '12px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)', border: '1px solid #edf2f7',
  },
  summaryLabel: { fontSize: '0.78rem', color: '#a0aec0', margin: '0 0 0.25rem', textTransform: 'uppercase' as const, letterSpacing: '0.05em', fontWeight: 500 },
  summaryValue: { fontSize: '1.4rem', fontWeight: 700, margin: 0 },
  insightBox: { background: '#ebf8ff', padding: '1.25rem', borderRadius: '12px', border: '1px solid #bee3f8' },
  recoBox: { background: '#fffff0', padding: '1.25rem', borderRadius: '12px', border: '1px solid #fefcbf' },
  sectionTitle: { fontSize: '0.95rem', fontWeight: 600, color: '#2d3748', margin: '0 0 0.75rem' },
  list: { margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column' as const, gap: '0.4rem' },
  listItem: { fontSize: '0.85rem', color: '#4a5568', lineHeight: 1.5 },
  metadata: { fontSize: '0.72rem', color: '#a0aec0', textAlign: 'center' as const, padding: '0.5rem 0' },
};
