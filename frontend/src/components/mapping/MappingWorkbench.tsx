import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { MappingService } from '../../services/api';
import { MappingSuggestion, MappingStatus, VarianceCategory, CostHead } from '../../services/types';
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

  useEffect(() => {
    sessionStorage.setItem('dss_mapping_draft_comment', comment);
  }, [comment]);

  useEffect(() => { loadPendingMappings(); }, []);

  const loadPendingMappings = async () => {
    try {
      setLoading(true);
      const data = await MappingService.getPendingMappings();
      setMappings(data);
    } catch (error) {
      toast.error('Failed to load pending mappings');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (mapping: MappingSuggestion) => {
    if (!comment.trim()) { toast.error('Please provide a comment'); return; }
    try {
      await MappingService.confirmMapping({ mapping_id: mapping.mapping_id, decision: 'Confirmed', comment, officer_name: officerName });
      toast.success('Mapping confirmed');
      setComment(''); setSelectedMapping(null); loadPendingMappings();
    } catch { toast.error('Failed to confirm mapping'); }
  };

  const handleOverride = async (mapping: MappingSuggestion) => {
    if (!comment.trim() || !overrideHead.trim()) { toast.error('Please provide a comment and override category'); return; }
    try {
      await MappingService.overrideMapping(mapping.mapping_id, overrideHead, overrideCategory, comment);
      toast.success('Mapping overridden');
      setComment(''); setOverrideHead(''); setSelectedMapping(null); loadPendingMappings();
    } catch { toast.error('Failed to override mapping'); }
  };

  const handleReject = async (mapping: MappingSuggestion) => {
    if (!comment.trim()) { toast.error('Please provide a reason for rejection'); return; }
    try {
      await MappingService.rejectMapping(mapping.mapping_id, comment);
      toast.success('Mapping rejected');
      setComment(''); setSelectedMapping(null); loadPendingMappings();
    } catch { toast.error('Failed to reject mapping'); }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <div style={{ textAlign: 'center' as const, color: '#718096' }}>
          <div style={{ width: '32px', height: '32px', border: '3px solid #e2e8f0', borderTopColor: '#3182ce', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 0.75rem' }} />
          Loading pending mappings...
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 style={s.pageTitle}>Mapping Workbench</h2>
      <p style={s.pageDesc}>
        Review and verify AI-suggested mappings before they enter the Rule Engine. All decisions are immutably logged.
      </p>

      {mappings.length === 0 ? (
        <div style={s.emptyState}>
          <span style={{ fontSize: '2rem' }}>✅</span>
          <p style={{ color: '#38a169', fontWeight: 600, margin: '0.5rem 0 0' }}>No pending mappings. All caught up!</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '1rem' }}>
          {mappings.map((mapping) => {
            const isSelected = selectedMapping?.mapping_id === mapping.mapping_id;
            const confidencePct = (mapping.confidence * 100).toFixed(0);
            const isLow = mapping.confidence < 0.7;
            return (
              <div key={mapping.mapping_id} style={{ ...s.card, ...(isSelected ? s.cardSelected : {}) }}>
                <div style={s.cardTop}>
                  <div style={s.cardTopLeft}>
                    <span style={s.sbuBadge}>{mapping.sbu_code}</span>
                    <span style={s.sourceField}>{mapping.source_field}</span>
                  </div>
                  <span style={{ ...s.confidence, color: isLow ? '#e53e3e' : '#38a169' }}>
                    {confidencePct}% {isLow && '⚠️'}
                  </span>
                </div>

                <div style={s.suggestion}>
                  AI suggests: <strong>{mapping.suggested_head}</strong> ({mapping.suggested_category})
                </div>
                <div style={s.reasoning}>{mapping.reasoning}</div>

                {isSelected ? (
                  <div style={s.actionPanel}>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Add your comment (required)..."
                      style={s.textarea}
                      rows={3}
                    />
                    <div style={s.btnRow}>
                      <button onClick={() => handleConfirm(mapping)} style={s.confirmBtn}>✅ Confirm</button>
                      <button onClick={() => handleReject(mapping)} style={s.rejectBtn}>❌ Reject</button>
                      <button onClick={() => setSelectedMapping(null)} style={s.cancelBtn}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setSelectedMapping(mapping)}
                    style={s.reviewBtn}
                    onMouseEnter={(e) => { e.currentTarget.style.color = '#2c5282'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = '#3182ce'; }}
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
  pageTitle: { fontSize: '1.35rem', fontWeight: 600, color: '#1a365d', margin: '0 0 0.5rem' },
  pageDesc: { fontSize: '0.9rem', color: '#718096', margin: '0 0 1.5rem' },
  emptyState: { textAlign: 'center' as const, padding: '3rem', background: '#f0fff4', borderRadius: '12px', border: '1px solid #c6f6d5' },
  card: {
    background: '#fff', borderRadius: '12px', padding: '1.25rem',
    border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)', transition: 'all 0.2s ease',
  },
  cardSelected: { borderColor: '#3182ce', background: '#f7faff', boxShadow: '0 0 0 3px rgba(49,130,206,0.1)' },
  cardTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' },
  cardTopLeft: { display: 'flex', alignItems: 'center', gap: '0.5rem' },
  sbuBadge: {
    fontSize: '0.7rem', fontWeight: 700, background: '#edf2f7', color: '#4a5568',
    padding: '0.2rem 0.5rem', borderRadius: '4px', textTransform: 'uppercase' as const,
  },
  sourceField: { fontSize: '0.95rem', fontWeight: 600, color: '#2d3748' },
  confidence: { fontSize: '0.85rem', fontWeight: 600 },
  suggestion: { fontSize: '0.85rem', color: '#4a5568', marginBottom: '0.25rem' },
  reasoning: { fontSize: '0.8rem', color: '#a0aec0', marginBottom: '0.75rem' },
  actionPanel: { marginTop: '1rem', borderTop: '1px solid #e2e8f0', paddingTop: '1rem' },
  textarea: {
    width: '100%', padding: '0.6rem 0.8rem', border: '1.5px solid #e2e8f0', borderRadius: '8px',
    fontSize: '0.85rem', fontFamily: 'inherit', resize: 'vertical' as const, marginBottom: '0.75rem',
    outline: 'none', boxSizing: 'border-box' as const, background: '#f7fafc',
  },
  btnRow: { display: 'flex', gap: '0.5rem' },
  confirmBtn: {
    padding: '0.5rem 1rem', background: '#38a169', color: '#fff', border: 'none',
    borderRadius: '6px', fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'inherit',
  },
  rejectBtn: {
    padding: '0.5rem 1rem', background: '#e53e3e', color: '#fff', border: 'none',
    borderRadius: '6px', fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'inherit',
  },
  cancelBtn: {
    padding: '0.5rem 1rem', background: '#edf2f7', color: '#4a5568', border: 'none',
    borderRadius: '6px', fontWeight: 500, fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'inherit',
  },
  reviewBtn: {
    background: 'none', border: 'none', color: '#3182ce', fontWeight: 600,
    fontSize: '0.85rem', cursor: 'pointer', padding: 0, fontFamily: 'inherit', transition: 'color 0.2s',
  },
};
