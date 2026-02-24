import React, { useState } from 'react';
import { EfficiencyService } from '../../services/api';
import { EfficiencyResponse } from '../../services/types';
import { toast } from 'react-toastify';
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export function EfficiencyAnalysis() {
    const [financialYear, setFinancialYear] = useState('2024-25');
    const [actualLoss, setActualLoss] = useState<string>('');
    const [result, setResult] = useState<EfficiencyResponse | null>(null);
    const [loading, setLoading] = useState(false);

    const handleEvaluate = async () => {
        if (!actualLoss || isNaN(Number(actualLoss))) {
            toast.error('Please enter a valid actual line loss percentage.');
            return;
        }

        setLoading(true);
        try {
            const data = await EfficiencyService.evaluateLineLoss(financialYear, Number(actualLoss));
            setResult(data);
            toast.success('Efficiency evaluated successfully.');
        } catch (error) {
            toast.error('Failed to evaluate efficiency parameters.');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={s.container}>
            <div style={s.headerRow}>
                <div>
                    <h2 style={s.title}>Operational Efficiency & Line Loss Analysis</h2>
                    <p style={s.subtitle}>Evaluates submitted T&D losses against normative KSERC trajectories.</p>
                </div>
            </div>

            <div style={s.controlsRow}>
                <div style={s.inputGroup}>
                    <label style={s.label}>Financial Year</label>
                    <select
                        value={financialYear}
                        onChange={(e) => setFinancialYear(e.target.value)}
                        style={s.input}
                    >
                        <option value="2022-23">2022-23</option>
                        <option value="2023-24">2023-24</option>
                        <option value="2024-25">2024-25</option>
                        <option value="2025-26">2025-26</option>
                        <option value="2026-27">2026-27</option>
                    </select>
                </div>

                <div style={s.inputGroup}>
                    <label style={s.label}>Actual Line Loss (%)</label>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <input
                            type="number"
                            step="0.01"
                            value={actualLoss}
                            onChange={(e) => setActualLoss(e.target.value)}
                            placeholder="e.g. 11.52"
                            style={{ ...s.input, width: '8rem' }}
                        />
                        <button
                            onClick={handleEvaluate}
                            disabled={loading}
                            style={{ ...s.button, opacity: loading ? 0.5 : 1 }}
                        >
                            {loading ? 'Evaluating...' : 'Evaluate'}
                        </button>
                    </div>
                </div>
            </div>

            {result && (
                <div style={result.is_violation ? s.resultBoxViolation : s.resultBoxSuccess}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                        {result.is_violation ? (
                            <ExclamationTriangleIcon style={{ width: '24px', height: '24px', color: '#e53e3e', marginTop: '4px' }} />
                        ) : (
                            <CheckCircleIcon style={{ width: '24px', height: '24px', color: '#38a169', marginTop: '4px' }} />
                        )}

                        <div style={{ width: '100%' }}>
                            <h3 style={{ ...s.resultTitle, color: result.is_violation ? '#9b2c2c' : '#276749' }}>
                                {result.is_violation ? 'Efficiency Violation Detected' : 'Efficiency Target Achieved'}
                            </h3>

                            <div style={s.statsGrid}>
                                <div>
                                    <p style={s.statLabel}>Normative Target</p>
                                    <p style={s.statValue}>{result.target_loss_percent}%</p>
                                </div>
                                <div>
                                    <p style={s.statLabel}>Actual Submission</p>
                                    <p style={{ ...s.statValue, color: result.is_violation ? '#c53030' : '#2f855a' }}>
                                        {result.actual_loss_percent}%
                                    </p>
                                </div>
                                <div>
                                    <p style={s.statLabel}>Deviation</p>
                                    <p style={s.statValue}>
                                        {result.deviation_percent > 0 ? '+' : ''}{result.deviation_percent}%
                                    </p>
                                </div>
                                {result.is_violation && (
                                    <div>
                                        <p style={{ ...s.statLabel, color: '#e53e3e', fontWeight: 600 }}>Est. Power Purchase Penalty</p>
                                        <p style={{ ...s.statValue, color: '#c53030', fontWeight: 700 }}>₹{result.penalty_estimate_cr} Cr</p>
                                    </div>
                                )}
                            </div>

                            <div style={s.logicBox}>
                                <strong>Logic Engine:</strong> {result.logic_applied} <br />
                                <span style={{ color: '#718096', fontStyle: 'italic', marginTop: '4px', display: 'inline-block' }}>{result.regulatory_clause}</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

const s: Record<string, React.CSSProperties> = {
    container: { background: '#fff', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginTop: '2rem', borderTop: '4px solid #319795' },
    headerRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' },
    title: { fontSize: '1.25rem', fontWeight: 700, color: '#2d3748', margin: '0 0 0.25rem 0' },
    subtitle: { fontSize: '0.875rem', color: '#718096', margin: 0 },
    controlsRow: { display: 'flex', gap: '1.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' as const },
    inputGroup: { display: 'flex', flexDirection: 'column' as const, gap: '0.25rem' },
    label: { fontSize: '0.875rem', fontWeight: 500, color: '#4a5568' },
    input: { border: '1px solid #cbd5e0', borderRadius: '4px', padding: '0.5rem 0.75rem', fontSize: '0.875rem', outline: 'none' },
    button: { padding: '0.5rem 1rem', background: '#319795', color: '#fff', border: 'none', borderRadius: '4px', fontSize: '0.875rem', cursor: 'pointer' },
    resultBoxSuccess: { padding: '1rem', borderRadius: '8px', border: '1px solid #c6f6d5', background: '#f0fff4' },
    resultBoxViolation: { padding: '1rem', borderRadius: '8px', border: '1px solid #fed7d7', background: '#fff5f5' },
    resultTitle: { fontSize: '1.125rem', fontWeight: 700, margin: '0 0 0.5rem 0' },
    statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem', marginBottom: '1rem' },
    statLabel: { fontSize: '0.875rem', color: '#4a5568', margin: '0 0 0.25rem 0' },
    statValue: { fontSize: '1.125rem', fontWeight: 500, margin: 0, color: '#2d3748' },
    logicBox: { fontSize: '0.875rem', background: 'rgba(255,255,255,0.6)', padding: '0.75rem', borderRadius: '4px' }
};
