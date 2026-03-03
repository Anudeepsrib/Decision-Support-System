import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { MappingService } from '../../services/api';
import { MappingSuggestion, MappingStatus, VarianceCategory } from '../../services/types';
import { useAuth } from '../../contexts/AuthContext';

export function MappingWorkbench() {
  const { user } = useAuth();
  const officerName = user?.full_name || 'Unknown Officer';

  const [mappings, setMappings] = useState<MappingSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMapping, setSelectedMapping] = useState<MappingSuggestion | null>(null);
  const [comment, setComment] = useState(
    () => sessionStorage.getItem('dss_mapping_draft_comment') || ''
  );
  const [overrideHead, setOverrideHead] = useState('');
  const [overrideCategory, setOverrideCategory] = useState<VarianceCategory>(VarianceCategory.CONTROLLABLE);
  const [processing, setProcessing] = useState(false);

  useEffect(() => { sessionStorage.setItem('dss_mapping_draft_comment', comment); }, [comment]);
  useEffect(() => { loadPendingMappings(); }, []);

  const loadPendingMappings = async () => {
    try {
      setLoading(true);
      const data = await MappingService.getPendingMappings();
      setMappings(data);
    } catch {
      toast.error('Failed to load pending mappings');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (mapping: MappingSuggestion) => {
    if (!comment.trim()) { toast.error('Please add a comment before confirming'); return; }
    try {
      setProcessing(true);
      await MappingService.confirmMapping({ mapping_id: mapping.mapping_id, decision: 'Confirmed', comment, officer_name: officerName });
      toast.success('✅ Mapping confirmed and logged');
      setComment(''); setSelectedMapping(null); loadPendingMappings();
    } catch { toast.error('Failed to confirm mapping'); }
    finally { setProcessing(false); }
  };

  const handleOverride = async (mapping: MappingSuggestion) => {
    if (!comment.trim() || !overrideHead.trim()) { toast.error('Please provide both a comment and override category'); return; }
    try {
      setProcessing(true);
      await MappingService.overrideMapping(mapping.mapping_id, overrideHead, overrideCategory, comment);
      toast.success('✏️ Mapping overridden');
      setComment(''); setOverrideHead(''); setSelectedMapping(null); loadPendingMappings();
    } catch { toast.error('Failed to override mapping'); }
    finally { setProcessing(false); }
  };

  const handleReject = async (mapping: MappingSuggestion) => {
    if (!comment.trim()) { toast.error('Please provide a rejection reason'); return; }
    try {
      setProcessing(true);
      await MappingService.rejectMapping(mapping.mapping_id, comment);
      toast.success('🚫 Mapping rejected and logged');
      setComment(''); setSelectedMapping(null); loadPendingMappings();
    } catch { toast.error('Failed to reject mapping'); }
    finally { setProcessing(false); }
  };

  const pending = mappings.filter(m => m.status === MappingStatus.PENDING);
  const reviewed = mappings.filter(m => m.status !== MappingStatus.PENDING);
  const progress = mappings.length > 0 ? (reviewed.length / mappings.length) * 100 : 0;

  if (loading) {
    return (
      <div style={s.loadingWrapper}>
        <div style={s.spinner} />
        <p style={s.loadingText}>Loading mapping workbench...</p>
      </div>
    );
  }

  return (
    <div className="slideUp">
      {/* ── Page Header ── */}
      <div style={s.pageHeader}>
        <div>
          <h2 style={s.pageTitle}>Mapping Workbench</h2>
          <p style={s.pageDesc}>
            Verify AI-suggested mappings before they enter the Rule Engine. All decisions are immutably logged.
          </p>
        </div>
        <button onClick={loadPendingMappings} style={s.refreshBtn}>
          ↻ Refresh
        </button>
      </div>

      {/* ── Progress Bar ── */}
      {mappings.length > 0 && (
        <div style={s.progressCard}>
          <div style={s.progressInfo}>
            <span style={s.progressLabel}>
              Review Progress: <strong>{reviewed.length}</strong> of <strong>{mappings.length}</strong> mappings completed
            </span>
            <span style={{ ...s.progressPct, color: progress === 100 ? '#276749' : '#2c5282' }}>
              {Math.round(progress)}%
            </span>
          </div>
          <div style={s.progressTrack}>
            <div style={{ ...s.progressFill, width: `${progress}%` }} />
          </div>
          {/* Status chips */}
          <div style={s.statusChips}>
            <span style={s.chipPending}>{pending.length} Pending</span>
            <span style={s.chipConfirmed}>{mappings.filter(m => m.status === MappingStatus.CONFIRMED).length} Confirmed</span>
            <span style={s.chipRejected}>{mappings.filter(m => m.status === MappingStatus.REJECTED).length} Rejected</span>
          </div>
        </div>
      )}

      {/* ── Empty State ── */}
      {mappings.length === 0 && (
        <div style={s.emptyState}>
          <div style={s.emptyIcon}>📭</div>
          <p style={s.emptyTitle}>No mappings yet</p>
          <p style={s.emptyDesc}>Upload a PDF document to generate AI-suggested mappings for review.</p>
        </div>
      )}

      {/* ── All Done ── */}
      {mappings.length > 0 && pending.length === 0 && (
        <div style={s.allDoneCard}>
          <span style={{ fontSize: '2rem' }}>🎉</span>
          <div>
            <p style={s.allDoneTitle}>All mappings reviewed!</p>
            <p style={s.allDoneDesc}>Head to Reports to generate your analytical report.</p>
          </div>
        </div>
      )}

      {/* ── Mapping Cards ── */}
      {pending.length > 0 && (
        <div style={s.cardList}>
          {pending.map((mapping) => {
            const isSelected = selectedMapping?.mapping_id === mapping.mapping_id;
            const pct = Math.round(mapping.confidence * 100);
            const tier = pct >= 80 ? 'high' : pct >= 55 ? 'medium' : 'low';
            const tierColor = { high: '#276749', medium: '#b45309', low: '#c53030' }[tier];
            const tierBg = { high: '#f0fff4', medium: '#fffbeb', low: '#fff5f5' }[tier];
            const tierBorder = { high: '#9ae6b4', medium: '#fbd38d', low: '#feb2b2' }[tier];

            return (
              <div
                key={mapping.mapping_id}
                style={{
                  ...s.card,
                  borderLeft: `4px solid ${tierBorder}`,
                  ...(isSelected ? s.cardSelected : {}),
                }}
              >
                {/* Card Top */}
                <div style={s.cardTop}>
                  <div style={s.cardTopLeft}>
                    <span style={s.sbuBadge}>{mapping.sbu_code}</span>
                    <span style={s.fieldName}>{mapping.source_field}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {/* Confidence pill */}
                    <span style={{ ...s.confPill, background: tierBg, color: tierColor, borderColor: tierBorder }}>
                      {tier === 'high' ? '🟢' : tier === 'medium' ? '🟡' : '🔴'} {pct}%
                    </span>
                  </div>
                </div>

                {/* Suggestion */}
                <div style={s.suggestionRow}>
                  <span style={s.aiLabel}>AI suggests</span>
                  <span style={s.suggTag}>{mapping.suggested_head}</span>
                  <span style={s.catTag}>{mapping.suggested_category}</span>
                </div>
                <p style={s.reasoning}>{mapping.reasoning}</p>

                {/* Confidence bar */}
                <div style={s.confTrack}>
                  <div style={{ ...s.confFill, width: `${pct}%`, background: tierColor }} />
                </div>

                {/* Action Panel (expanded) */}
                {isSelected ? (
                  <div style={s.actionPanel}>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Add your comment (required for audit trail)..."
                      style={s.textarea}
                      rows={2}
                    />
                    <div style={s.btnRow}>
                      <button
                        onClick={() => handleConfirm(mapping)}
                        disabled={processing}
                        style={s.confirmBtn}
                        onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-1px)'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; }}
                      >
                        {processing ? '...' : '✅ Confirm'}
                      </button>
                      <button
                        onClick={() => handleReject(mapping)}
                        disabled={processing}
                        style={s.rejectBtn}
                        onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-1px)'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; }}
                      >
                        {processing ? '...' : '❌ Reject'}
                      </button>
                      <button
                        onClick={() => setSelectedMapping(null)}
                        style={s.cancelBtn}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setSelectedMapping(mapping)}
                    style={s.reviewBtn}
                    onMouseEnter={(e) => { e.currentTarget.style.background = '#ebf8ff'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    Review →
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  loadingWrapper: { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', padding: '4rem', gap: '1rem' },
  spinner: { width: '36px', height: '36px', border: '3px solid #ebf8ff', borderTopColor: '#3182ce', borderRadius: '50%', animation: 'spin 0.8s linear infinite' },
  loadingText: { color: '#a0aec0', fontSize: '0.88rem', margin: 0 },

  pageHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' },
  pageTitle: { fontSize: '1.4rem', fontWeight: 800, color: '#1a202c', margin: '0 0 0.3rem' },
  pageDesc: { fontSize: '0.85rem', color: '#718096', margin: 0, lineHeight: 1.6 },
  refreshBtn: {
    fontSize: '0.8rem', background: '#f7fafc', color: '#4a5568',
    border: '1.5px solid #e2e8f0', padding: '0.4rem 0.9rem',
    borderRadius: '8px', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600, flexShrink: 0,
  },

  // Progress
  progressCard: {
    background: '#fff', borderRadius: '16px', padding: '1.25rem 1.5rem',
    boxShadow: '0 1px 6px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0',
    marginBottom: '1.25rem',
  },
  progressInfo: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' },
  progressLabel: { fontSize: '0.85rem', color: '#4a5568' },
  progressPct: { fontSize: '1.1rem', fontWeight: 800 },
  progressTrack: { height: '8px', background: '#f0f4f8', borderRadius: '999px', overflow: 'hidden', marginBottom: '0.75rem' },
  progressFill: { height: '100%', background: 'linear-gradient(90deg, #2c5282, #3182ce)', borderRadius: '999px', transition: 'width 0.6s ease' },
  statusChips: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' as const },
  chipPending: { fontSize: '0.72rem', padding: '0.2rem 0.6rem', borderRadius: '999px', background: '#ebf8ff', color: '#2c5282', fontWeight: 600 },
  chipConfirmed: { fontSize: '0.72rem', padding: '0.2rem 0.6rem', borderRadius: '999px', background: '#f0fff4', color: '#276749', fontWeight: 600 },
  chipRejected: { fontSize: '0.72rem', padding: '0.2rem 0.6rem', borderRadius: '999px', background: '#fff5f5', color: '#c53030', fontWeight: 600 },

  // Empty / Done
  emptyState: {
    background: '#fff', borderRadius: '20px', padding: '4rem 2rem',
    textAlign: 'center' as const, border: '1px solid #e2e8f0',
  },
  emptyIcon: { fontSize: '3rem', marginBottom: '0.75rem' },
  emptyTitle: { fontSize: '1.1rem', fontWeight: 700, color: '#2d3748', margin: '0 0 0.4rem' },
  emptyDesc: { fontSize: '0.85rem', color: '#a0aec0', margin: 0 },
  allDoneCard: {
    background: '#f0fff4', border: '1.5px solid #9ae6b4', borderRadius: '16px',
    padding: '1.25rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem',
  },
  allDoneTitle: { fontSize: '1rem', fontWeight: 700, color: '#22543d', margin: '0 0 0.2rem' },
  allDoneDesc: { fontSize: '0.82rem', color: '#276749', margin: 0 },

  // Cards
  cardList: { display: 'flex', flexDirection: 'column' as const, gap: '0.9rem' },
  card: {
    background: '#fff', borderRadius: '14px', padding: '1.25rem 1.25rem 1.25rem 1.5rem',
    border: '1px solid #e2e8f0', boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    transition: 'box-shadow 0.2s ease, transform 0.2s ease',
  },
  cardSelected: {
    border: '1px solid #3182ce', boxShadow: '0 0 0 3px rgba(49,130,206,0.1)',
    background: '#fafcff',
  },

  cardTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' },
  cardTopLeft: { display: 'flex', alignItems: 'center', gap: '0.5rem' },
  sbuBadge: {
    fontSize: '0.68rem', fontWeight: 700, background: '#edf2f7', color: '#2d3748',
    padding: '0.18rem 0.5rem', borderRadius: '5px', letterSpacing: '0.05em',
  },
  fieldName: { fontSize: '0.98rem', fontWeight: 700, color: '#1a202c' },
  confPill: {
    fontSize: '0.75rem', fontWeight: 700, padding: '0.2rem 0.6rem',
    borderRadius: '999px', border: '1px solid',
  },

  suggestionRow: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem', flexWrap: 'wrap' as const },
  aiLabel: { fontSize: '0.75rem', color: '#a0aec0', fontWeight: 500 },
  suggTag: {
    fontSize: '0.78rem', fontWeight: 700, background: '#ebf8ff', color: '#2c5282',
    padding: '0.15rem 0.5rem', borderRadius: '5px',
  },
  catTag: {
    fontSize: '0.75rem', fontWeight: 600, background: '#f0fff4', color: '#276749',
    padding: '0.15rem 0.5rem', borderRadius: '5px', border: '1px solid #9ae6b4',
  },
  reasoning: { fontSize: '0.78rem', color: '#a0aec0', marginBottom: '0.65rem', lineHeight: 1.5 },
  confTrack: { height: '4px', background: '#f0f4f8', borderRadius: '999px', overflow: 'hidden', marginBottom: '0.85rem' },
  confFill: { height: '100%', borderRadius: '999px', opacity: 0.7, transition: 'width 0.5s ease' },

  // Action Panel
  actionPanel: { borderTop: '1px solid #f0f4f8', paddingTop: '1rem', marginTop: '0.25rem' },
  textarea: {
    width: '100%', padding: '0.6rem 0.8rem', border: '1.5px solid #e2e8f0',
    borderRadius: '8px', fontSize: '0.84rem', fontFamily: 'Inter, sans-serif',
    resize: 'vertical' as const, marginBottom: '0.75rem', outline: 'none',
    boxSizing: 'border-box' as const, background: '#f8fafc', lineHeight: 1.5,
    transition: 'border-color 0.2s, box-shadow 0.2s',
  },
  btnRow: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' as const },
  confirmBtn: {
    padding: '0.5rem 1.1rem', background: 'linear-gradient(135deg, #276749, #38a169)',
    color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 700,
    fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'inherit',
    boxShadow: '0 2px 8px rgba(56,161,105,0.3)', transition: 'transform 0.15s ease',
  },
  rejectBtn: {
    padding: '0.5rem 1.1rem', background: 'linear-gradient(135deg, #9b2c2c, #c53030)',
    color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 700,
    fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'inherit',
    boxShadow: '0 2px 8px rgba(197,48,48,0.25)', transition: 'transform 0.15s ease',
  },
  cancelBtn: {
    padding: '0.5rem 1rem', background: '#f0f4f8', color: '#718096',
    border: 'none', borderRadius: '8px', fontWeight: 600,
    fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'inherit',
  },
  reviewBtn: {
    background: 'transparent', border: 'none', color: '#3182ce',
    fontWeight: 700, fontSize: '0.83rem', cursor: 'pointer',
    padding: '0.3rem 0.6rem', borderRadius: '6px',
    fontFamily: 'inherit', transition: 'background 0.2s ease',
  },
};
