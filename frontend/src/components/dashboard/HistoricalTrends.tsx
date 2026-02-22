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
        return <div className="p-4 text-gray-500 animate-pulse">Loading historical insights...</div>;
    }

    if (data.length === 0) {
        return <div className="p-4 text-gray-500">No historical data available.</div>;
    }

    // Format currency down to Crores for clean presentation
    const formatYAxis = (tickItem: number) => `₹${(tickItem / 1e7).toFixed(0)}Cr`;
    const formatTooltipCurrency = (value: number) => `₹${(value / 1e7).toFixed(2)} Cr`;
    const formatTooltipPercent = (value: number) => `${value}%`;

    return (
        <div className="space-y-6 mt-8">
            <div className="border-b pb-2">
                <h2 className="text-2xl font-bold text-gray-800">Multi-Year Historical Trends</h2>
                <p className="text-gray-500">Year-over-Year tracking of key metrics against Truing-Up baseline averages.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Approved vs Actual ARR Trajectory (Bar) */}
                <div className="bg-white p-4 rounded-lg shadow border border-gray-100">
                    <h3 className="text-lg font-semibold text-gray-700 mb-4 text-center">ARR Trajectory (Approved vs Actual)</h3>
                    <div className="h-64 w-full">
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
                <div className="bg-white p-4 rounded-lg shadow border border-gray-100">
                    <h3 className="text-lg font-semibold text-gray-700 mb-4 text-center">Operational Cost Dynamics</h3>
                    <div className="h-64 w-full">
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
                <div className="bg-white p-4 rounded-lg shadow border border-gray-100">
                    <h3 className="text-lg font-semibold text-gray-700 mb-4 text-center">T&D Line Loss Progression (%)</h3>
                    <div className="h-64 w-full">
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
                <div className="bg-white p-4 rounded-lg shadow border border-gray-100">
                    <h3 className="text-lg font-semibold text-gray-700 mb-4 text-center">Net Revenue Gap Magnitude</h3>
                    <div className="h-64 w-full">
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
