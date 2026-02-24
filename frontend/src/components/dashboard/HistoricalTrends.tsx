import React, { useEffect, useState } from 'react';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { HistoryService } from '../../services/api';
import { HistoricalTrendData } from '../../services/types';
import { toast } from 'react-toastify';

export function HistoricalTrends() {
    const [data, setData] = useState<HistoricalTrendData[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadTrends() {
            try {
                const trends = await HistoryService.getTrends();
                setData(trends);
            } catch (error) {
                toast.error('Failed to load historical trends');
                console.error(error);
            } finally {
                setLoading(false);
            }
        }
        loadTrends();
    }, []);

    if (loading) {
        return <div style={{ padding: '1rem', color: '#718096' }}>Loading historical insights...</div>;
    }

    if (data.length === 0) {
        return <div style={{ padding: '1rem', color: '#718096' }}>No historical data available.</div>;
    }

    const formatYAxis = (tickItem: number) => `₹${(tickItem / 1e7).toFixed(0)}Cr`;
    const formatTooltipCurrency = (value: number) => `₹${(value / 1e7).toFixed(2)} Cr`;
    const formatTooltipPercent = (value: number) => `${value}%`;

    return (
        <div style={s.container}>
            <div style={s.header}>
                <h2 style={s.title}>Multi-Year Historical Trends</h2>
                <p style={s.subtitle}>Year-over-Year tracking of key metrics against Truing-Up baseline averages.</p>
            </div>

            <div style={s.grid}>
                {/* Approved vs Actual ARR Trajectory (Bar) */}
                <div style={s.card}>
                    <h3 style={s.cardTitle}>ARR Trajectory (Approved vs Actual)</h3>
                    <div style={s.chartWrapper}>
                        <ResponsiveContainer>
                            <BarChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="financial_year" />
                                <YAxis tickFormatter={formatYAxis} width={80} />
                                <Tooltip formatter={formatTooltipCurrency} cursor={{ fill: '#f3f4f6' }} />
                                <Legend />
                                <Bar dataKey="total_approved_arr" name="Approved ARR" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                                <Bar dataKey="total_actual_arr" name="Actual ARR" fill="#10B981" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Operational Cost Dynamics (Line) */}
                <div style={s.card}>
                    <h3 style={s.cardTitle}>Operational Cost Dynamics</h3>
                    <div style={s.chartWrapper}>
                        <ResponsiveContainer>
                            <LineChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="financial_year" />
                                <YAxis tickFormatter={formatYAxis} width={80} />
                                <Tooltip formatter={formatTooltipCurrency} />
                                <Legend />
                                <Line type="monotone" dataKey="power_purchase_cost" name="Power Purchase" stroke="#EF4444" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                                <Line type="monotone" dataKey="o_and_m_cost" name="O&M Cost" stroke="#F59E0B" strokeWidth={3} />
                                <Line type="monotone" dataKey="staff_cost" name="Staff Cost" stroke="#8B5CF6" strokeWidth={3} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Line Loss Efficiency (Line) */}
                <div style={s.card}>
                    <h3 style={s.cardTitle}>T&D Line Loss Progression (%)</h3>
                    <div style={s.chartWrapper}>
                        <ResponsiveContainer>
                            <LineChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="financial_year" />
                                <YAxis width={40} domain={['dataMin - 1', 'dataMax + 1']} />
                                <Tooltip formatter={formatTooltipPercent} />
                                <Legend />
                                <Line type="monotone" dataKey="line_loss_percent" name="Actual Line Loss" stroke="#EC4899" strokeWidth={4} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Net Revenue Gap Magnitude (Bar) */}
                <div style={s.card}>
                    <h3 style={s.cardTitle}>Net Revenue Gap Magnitude</h3>
                    <div style={s.chartWrapper}>
                        <ResponsiveContainer>
                            <BarChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="financial_year" />
                                <YAxis tickFormatter={formatYAxis} width={80} />
                                <Tooltip formatter={formatTooltipCurrency} cursor={{ fill: '#f3f4f6' }} />
                                <Legend />
                                <Bar dataKey="revenue_gap" name="Revenue Gap (Deficit)" fill="#6366F1" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}

const s: Record<string, React.CSSProperties> = {
    container: { marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' },
    header: { borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' },
    title: { fontSize: '1.5rem', fontWeight: 700, color: '#2d3748', margin: '0 0 0.25rem 0' },
    subtitle: { color: '#718096', margin: 0, fontSize: '0.9rem' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' },
    card: { background: '#fff', padding: '1rem', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid #edf2f7' },
    cardTitle: { fontSize: '1.125rem', fontWeight: 600, color: '#4a5568', marginBottom: '1rem', textAlign: 'center' },
    chartWrapper: { height: '16rem', width: '100%' }
};
