import React, { useState, useRef, useCallback } from 'react';
import { ComparisonService } from '../../services/api';
import type { OrderComparisonResponse, FieldComparison, ItemComparison } from '../../services/types';

// ─── Anomaly Emoji + Color System ───
const ANOMALY = {
    MATCH: { emoji: '✅', label: 'Match', bg: '#d4edda', text: '#155724', border: '#c3e6cb' },
    MISMATCH: { emoji: '❌', label: 'Mismatch', bg: '#f8d7da', text: '#721c24', border: '#f5c6cb' },
    MISSING_IN_REFERENCE: { emoji: '⚠️', label: 'Missing', bg: '#fff3cd', text: '#856404', border: '#ffeeba' },
    EXTRA_IN_REFERENCE: { emoji: 'ℹ️', label: 'Extra', bg: '#d1ecf1', text: '#0c5460', border: '#bee5eb' },
    NOT_FOUND: { emoji: '🔍', label: 'Not Found', bg: '#e2e3e5', text: '#383d41', border: '#d6d8db' },
} as Record<string, { emoji: string; label: string; bg: string; text: string; border: string }>;

const RISK = {
    LOW: { emoji: '🟢', color: '#28a745', bg: 'rgba(40,167,69,0.1)' },
    MEDIUM: { emoji: '🟡', color: '#ffc107', bg: 'rgba(255,193,7,0.1)' },
    HIGH: { emoji: '🔴', color: '#dc3545', bg: 'rgba(220,53,69,0.1)' },
};

function AnomalyBadge({ status }: { status: string }) {
    const key = status.toUpperCase();
    const a = ANOMALY[key] || ANOMALY.NOT_FOUND;
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
            padding: '0.25rem 0.65rem', borderRadius: '999px',
            fontSize: '0.72rem', fontWeight: 700,
            background: a.bg, color: a.text, border: `1px solid ${a.border}`,
        }}>
            {a.emoji} {a.label}
        </span>
    );
}

// ─── Bar Chart Component (pure CSS) ───
function BarChart({ data }: { data: { label: string; value: number; color: string }[] }) {
    const max = Math.max(...data.map(d => d.value), 1);
    return (
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.75rem', height: '120px', padding: '0.5rem 0' }}>
            {data.map((d, i) => (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
                    <span style={{ fontSize: '1.1rem', fontWeight: 800, color: d.color, marginBottom: '0.3rem' }}>
                        {d.value}
                    </span>
                    <div style={{
                        width: '100%', maxWidth: '48px',
                        height: `${Math.max(8, (d.value / max) * 80)}px`,
                        background: `linear-gradient(180deg, ${d.color} 0%, ${d.color}88 100%)`,
                        borderRadius: '6px 6px 2px 2px',
                        transition: 'height 0.5s ease',
                        boxShadow: `0 2px 8px ${d.color}44`,
                    }} />
                    <span style={{ fontSize: '0.62rem', color: '#718096', marginTop: '0.4rem', textAlign: 'center', fontWeight: 600 }}>
                        {d.label}
                    </span>
                </div>
            ))}
        </div>
    );
}

// ─── Confidence Ring (SVG donut) ───
function ConfidenceRing({ score }: { score: number }) {
    const pct = Math.min(100, Math.max(0, score));
    const color = pct >= 80 ? '#28a745' : pct >= 50 ? '#ffc107' : '#dc3545';
    const circumference = 2 * Math.PI * 40;
    const offset = circumference - (pct / 100) * circumference;
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <svg width="90" height="90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" stroke="#e9ecef" strokeWidth="8" fill="none" />
                <circle cx="50" cy="50" r="40" stroke={color} strokeWidth="8" fill="none"
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    strokeLinecap="round" transform="rotate(-90 50 50)"
                    style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
                <text x="50" y="50" textAnchor="middle" dy="0.35em"
                    fontSize="20" fontWeight="800" fill={color}>
                    {pct}
                </text>
            </svg>
            <div>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#2d3748' }}>Confidence</div>
                <div style={{ fontSize: '0.7rem', color: '#718096' }}>
                    {pct >= 80 ? '🟢 High extraction clarity' : pct >= 50 ? '🟡 Moderate clarity' : '🔴 Low clarity'}
                </div>
            </div>
        </div>
    );
}

export function OrderComparison() {
    const [orderFile, setOrderFile] = useState<File | null>(null);
    const [referenceFile, setReferenceFile] = useState<File | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<OrderComparisonResponse | null>(null);

    const orderRef = useRef<HTMLInputElement>(null);
    const refRef = useRef<HTMLInputElement>(null);

    const handleCompare = useCallback(async () => {
        if (!orderFile || !referenceFile) {
            setError('Please select both an Order PDF and a Reference PDF.');
            return;
        }
        setError(null);
        setIsLoading(true);
        try {
            const data = await ComparisonService.compareOrders(orderFile, referenceFile);
            setResult(data);
        } catch (e: any) {
            setError(e.message || 'Comparison failed.');
        } finally {
            setIsLoading(false);
        }
    }, [orderFile, referenceFile]);

    const handleDrop = useCallback((e: React.DragEvent, setter: (f: File) => void) => {
        e.preventDefault();
        e.stopPropagation();
        const file = e.dataTransfer.files[0];
        if (file) setter(file);
    }, []);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
    }, []);

    // Derive risk from summary
    const riskLevel = (() => {
        if (!result) return '';
        const s = result.summary;
        const miss = parseInt(s.missing_items || '0');
        const ext = parseInt(s.extra_items || '0');
        const mis = parseInt(s.mismatched_items || '0');
        if (miss > 0 || ext > 0) return 'HIGH';
        if (mis > 0) return 'MEDIUM';
        return 'LOW';
    })();

    const summaryChartData = result ? [
        { label: 'Matched', value: parseInt(result.summary.matched_items || '0'), color: '#28a745' },
        { label: 'Mismatched', value: parseInt(result.summary.mismatched_items || '0'), color: '#dc3545' },
        { label: 'Missing', value: parseInt(result.summary.missing_items || '0'), color: '#ffc107' },
        { label: 'Extra', value: parseInt(result.summary.extra_items || '0'), color: '#17a2b8' },
    ] : [];

    return (
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: '1.5rem' }}>
                <h2 style={st.pageTitle}>📋 Order Comparison — Anomaly Detection</h2>
                <p style={st.pageSub}>
                    Deterministic document comparison engine. Upload Order + Reference PDFs to detect discrepancies.
                </p>
                <div style={{
                    marginTop: '0.4rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                    padding: '0.2rem 0.6rem', borderRadius: '999px', background: '#e2e3e5', fontSize: '0.68rem', color: '#495057', fontWeight: 600
                }}>
                    ⚙️ No LLM required — fully rule-based
                </div>
            </div>

            {/* Upload Zone */}
            <div style={st.card}>
                <h3 style={st.sectionTitle}>📤 Upload Documents</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', marginBottom: '1.25rem' }}>
                    {/* Order */}
                    <div
                        id="order-upload-zone"
                        style={{ ...st.dropZone, borderColor: orderFile ? '#28a745' : '#ced4da', background: orderFile ? '#f1f8f1' : '#fafbfc' }}
                        onDrop={(e) => handleDrop(e, setOrderFile)} onDragOver={handleDragOver}
                        onClick={() => orderRef.current?.click()}
                    >
                        <input ref={orderRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp" style={{ display: 'none' }}
                            onChange={(e) => e.target.files?.[0] && setOrderFile(e.target.files[0])} />
                        <div style={{ fontSize: '2.5rem' }}>{orderFile ? '✅' : '📄'}</div>
                        <div style={st.dropLabel}>{orderFile ? orderFile.name : 'Order PDF'}</div>
                        <div style={st.dropHint}>Drop file or click to browse</div>
                    </div>
                    {/* Reference */}
                    <div
                        id="reference-upload-zone"
                        style={{ ...st.dropZone, borderColor: referenceFile ? '#28a745' : '#ced4da', background: referenceFile ? '#f1f8f1' : '#fafbfc' }}
                        onDrop={(e) => handleDrop(e, setReferenceFile)} onDragOver={handleDragOver}
                        onClick={() => refRef.current?.click()}
                    >
                        <input ref={refRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp" style={{ display: 'none' }}
                            onChange={(e) => e.target.files?.[0] && setReferenceFile(e.target.files[0])} />
                        <div style={{ fontSize: '2.5rem' }}>{referenceFile ? '✅' : '📑'}</div>
                        <div style={st.dropLabel}>{referenceFile ? referenceFile.name : 'Reference PDF'}</div>
                        <div style={st.dropHint}>Drop file or click to browse</div>
                    </div>
                </div>

                {error && <div style={st.errorBox}>❌ {error}</div>}

                <button id="compare-btn" onClick={handleCompare}
                    disabled={isLoading || !orderFile || !referenceFile}
                    style={{
                        ...st.primaryBtn, opacity: isLoading || !orderFile || !referenceFile ? 0.5 : 1,
                        cursor: isLoading || !orderFile || !referenceFile ? 'not-allowed' : 'pointer'
                    }}>
                    {isLoading ? '⏳ Analyzing Documents...' : '🔍 Compare Documents'}
                </button>
            </div>

            {/* ═══ RESULTS ═══ */}
            {result && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '1.5rem' }}>

                    {/* Top Row: Chart + Confidence + Risk */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr', gap: '1.25rem' }}>
                        {/* Bar Chart */}
                        <div style={st.card}>
                            <h4 style={st.miniTitle}>📊 Anomaly Distribution</h4>
                            <BarChart data={summaryChartData} />
                        </div>

                        {/* Confidence Ring */}
                        <div style={st.card}>
                            <h4 style={st.miniTitle}>🎯 Confidence Score</h4>
                            <ConfidenceRing score={parseFloat(result.confidence_score) || 0} />
                        </div>

                        {/* Risk Assessment */}
                        <div style={st.card}>
                            <h4 style={st.miniTitle}>🚦 Risk Assessment</h4>
                            {riskLevel && (
                                <div style={{
                                    padding: '0.75rem 1rem', borderRadius: '10px',
                                    background: RISK[riskLevel as keyof typeof RISK]?.bg,
                                    border: `2px solid ${RISK[riskLevel as keyof typeof RISK]?.color}20`,
                                    display: 'flex', alignItems: 'center', gap: '0.75rem',
                                }}>
                                    <span style={{ fontSize: '2rem' }}>{RISK[riskLevel as keyof typeof RISK]?.emoji}</span>
                                    <div>
                                        <div style={{ fontSize: '1.2rem', fontWeight: 800, color: RISK[riskLevel as keyof typeof RISK]?.color }}>
                                            {riskLevel} RISK
                                        </div>
                                        <div style={{ fontSize: '0.72rem', color: '#6c757d' }}>
                                            {riskLevel === 'HIGH' ? '🚨 Missing or extra items detected'
                                                : riskLevel === 'MEDIUM' ? '⚠️ Item discrepancies found'
                                                    : '✅ All items match'}
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div style={{ fontSize: '0.68rem', color: '#adb5bd', marginTop: '0.5rem' }}>
                                Job ID: <code>{result.job_id}</code>
                            </div>
                        </div>
                    </div>

                    {/* Summary Stats Row */}
                    <div style={{ ...st.card, display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
                        <StatCell emoji="📦" label="Total Items" value={result.summary.total_items_order} />
                        <StatCell emoji="✅" label="Matched" value={result.summary.matched_items} color="#28a745" />
                        <StatCell emoji="❌" label="Mismatched" value={result.summary.mismatched_items} color="#dc3545" />
                        <StatCell emoji="⚠️" label="Missing" value={result.summary.missing_items} color="#ffc107" />
                        <StatCell emoji="ℹ️" label="Extra" value={result.summary.extra_items} color="#17a2b8" />
                        <StatCell emoji="🏷️" label="Status" value={result.summary.overall_status} color="#6f42c1" small />
                    </div>

                    {/* Order-Level Comparison Table */}
                    <div style={st.card}>
                        <h3 style={st.sectionTitle}>🔎 Order-Level Comparison</h3>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={st.table}>
                                <thead>
                                    <tr>
                                        <th style={st.th}>Field</th>
                                        <th style={st.th}>Order Value</th>
                                        <th style={st.th}>Reference Value</th>
                                        <th style={st.th}>Anomaly</th>
                                        <th style={st.th}>Reason</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {Object.entries(result.order_level_comparison).map(([name, field]) => {
                                        const f = field as FieldComparison;
                                        return (
                                            <tr key={name} style={{ background: f.status === 'MISMATCH' ? '#fff5f5' : 'transparent' }}>
                                                <td style={st.td}><strong>{name.replace(/_/g, ' ')}</strong></td>
                                                <td style={st.td}>{f.order_value || '—'}</td>
                                                <td style={st.td}>{f.reference_value || '—'}</td>
                                                <td style={st.td}><AnomalyBadge status={f.status} /></td>
                                                <td style={{ ...st.td, fontSize: '0.78rem', color: '#6c757d' }}>{f.reason || '—'}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Item-Level Comparison Table */}
                    {result.items_comparison.length > 0 && (
                        <div style={st.card}>
                            <h3 style={st.sectionTitle}>📋 Item-Level Comparison</h3>
                            <div style={{ overflowX: 'auto' }}>
                                <table style={st.table}>
                                    <thead>
                                        <tr>
                                            <th style={st.th}>Product (Order)</th>
                                            <th style={st.th}>Product (Ref)</th>
                                            <th style={st.th}>Qty (O/R)</th>
                                            <th style={st.th}>Unit Price (O/R)</th>
                                            <th style={st.th}>Total (O/R)</th>
                                            <th style={st.th}>Anomaly</th>
                                            <th style={st.th}>Reason</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.items_comparison.map((item: ItemComparison, idx: number) => (
                                            <tr key={idx} style={{ background: item.status === 'MISMATCH' ? '#fff5f5' : 'transparent' }}>
                                                <td style={st.td}>{item.product_name_order || '—'}</td>
                                                <td style={st.td}>{item.product_name_reference || '—'}</td>
                                                <td style={st.td}>{item.quantity_order} / {item.quantity_reference}</td>
                                                <td style={st.td}>{item.unit_price_order} / {item.unit_price_reference}</td>
                                                <td style={st.td}>{item.total_price_order} / {item.total_price_reference}</td>
                                                <td style={st.td}><AnomalyBadge status={item.status} /></td>
                                                <td style={{ ...st.td, fontSize: '0.78rem', color: '#6c757d', maxWidth: '200px' }}>{item.reason || '—'}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Missing / Extra Flag Cards */}
                    {(result.missing_items_in_reference.length > 0 || result.extra_items_in_reference.length > 0) && (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
                            {result.missing_items_in_reference.length > 0 && (
                                <div style={{ ...st.card, borderLeft: '4px solid #ffc107' }}>
                                    <h4 style={st.miniTitle}>⚠️ Missing in Reference — Flagged</h4>
                                    {result.missing_items_in_reference.map((item, i) => (
                                        <div key={i} style={{
                                            display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0',
                                            borderBottom: '1px solid #f0f0f0', fontSize: '0.85rem', color: '#495057'
                                        }}>
                                            <span style={{ fontSize: '1.1rem' }}>🚨</span> {item}
                                        </div>
                                    ))}
                                </div>
                            )}
                            {result.extra_items_in_reference.length > 0 && (
                                <div style={{ ...st.card, borderLeft: '4px solid #17a2b8' }}>
                                    <h4 style={st.miniTitle}>ℹ️ Extra in Reference</h4>
                                    {result.extra_items_in_reference.map((item, i) => (
                                        <div key={i} style={{
                                            display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0',
                                            borderBottom: '1px solid #f0f0f0', fontSize: '0.85rem', color: '#495057'
                                        }}>
                                            <span style={{ fontSize: '1.1rem' }}>📌</span> {item}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Executive Report */}
                    <div style={st.card}>
                        <h3 style={st.sectionTitle}>📝 Deterministic Report</h3>
                        <pre style={{
                            background: '#f8f9fa', borderRadius: '8px', padding: '1.25rem',
                            fontSize: '0.82rem', lineHeight: 1.7, color: '#212529',
                            border: '1px solid #dee2e6', whiteSpace: 'pre-wrap', fontFamily: "'JetBrains Mono', Consolas, monospace",
                            margin: 0,
                        }}>
                            {result.executive_report}
                        </pre>
                    </div>

                    {/* LLM Report (optional) */}
                    {result.llm_report && result.llm_report !== 'LLM_REPORT_DISABLED' && !result.llm_report.startsWith('LLM_REPORT_ERROR') && (
                        <div style={st.card}>
                            <h3 style={st.sectionTitle}>🤖 AI-Generated Report (Optional)</h3>
                            <div style={{
                                background: 'linear-gradient(135deg, #f0f4ff 0%, #e8ecf9 100%)',
                                borderRadius: '8px', padding: '1.25rem', fontSize: '0.88rem',
                                lineHeight: 1.7, color: '#2d3748', border: '1px solid #c3cfe2',
                                whiteSpace: 'pre-wrap',
                            }}>
                                {result.llm_report}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function StatCell({ emoji, label, value, color, small }: {
    emoji: string; label: string; value: string; color?: string; small?: boolean;
}) {
    return (
        <div>
            <div style={{ fontSize: '1.1rem' }}>{emoji}</div>
            <div style={{ fontSize: small ? '0.78rem' : '1.3rem', fontWeight: 800, color: color || '#212529' }}>
                {value || '0'}
            </div>
            <div style={{ fontSize: '0.62rem', color: '#adb5bd', fontWeight: 600, letterSpacing: '0.04em' }}>{label}</div>
        </div>
    );
}

// ─── Styles ───
const st: Record<string, React.CSSProperties> = {
    pageTitle: { fontSize: '1.5rem', fontWeight: 800, color: '#1a202c', margin: 0, letterSpacing: '-0.02em' },
    pageSub: { fontSize: '0.88rem', color: '#718096', margin: '0.3rem 0 0 0' },
    card: {
        background: '#ffffff', borderRadius: '12px', padding: '1.5rem',
        border: '1px solid #e2e8f0', boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    },
    sectionTitle: { fontSize: '1rem', fontWeight: 700, color: '#2d3748', margin: '0 0 1rem 0' },
    miniTitle: { fontSize: '0.82rem', fontWeight: 700, color: '#4a5568', margin: '0 0 0.75rem 0' },
    dropZone: {
        border: '2px dashed #ced4da', borderRadius: '10px', padding: '2rem 1.5rem',
        textAlign: 'center' as const, cursor: 'pointer', transition: 'all 0.2s ease',
    },
    dropLabel: { fontSize: '0.88rem', fontWeight: 600, color: '#2d3748', wordBreak: 'break-all' as const },
    dropHint: { fontSize: '0.72rem', color: '#adb5bd', marginTop: '0.3rem' },
    errorBox: {
        background: '#f8d7da', border: '1px solid #f5c6cb', borderRadius: '8px',
        padding: '0.75rem 1rem', fontSize: '0.85rem', color: '#721c24', marginBottom: '1rem',
    },
    primaryBtn: {
        width: '100%', padding: '0.85rem',
        background: 'linear-gradient(135deg, #2c5282 0%, #3182ce 100%)',
        color: '#fff', border: 'none', borderRadius: '10px',
        fontSize: '0.92rem', fontWeight: 700, fontFamily: 'inherit', transition: 'all 0.2s ease',
    },
    table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '0.83rem' },
    th: {
        textAlign: 'left' as const, padding: '0.65rem 0.75rem',
        borderBottom: '2px solid #dee2e6', color: '#6c757d',
        fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' as const,
    },
    td: {
        padding: '0.65rem 0.75rem', borderBottom: '1px solid #f0f0f0',
        color: '#212529', verticalAlign: 'top' as const,
    },
};
