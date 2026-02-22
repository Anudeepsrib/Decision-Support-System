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
        <div className="bg-white p-6 rounded-lg shadow mt-8 border-t-4 border-teal-500">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-xl font-bold text-gray-800">Operational Efficiency & Line Loss Analysis</h2>
                    <p className="text-sm text-gray-500">Evaluates submitted T&D losses against normative KSERC trajectories.</p>
                </div>
            </div>

            <div className="flex flex-col md:flex-row gap-4 mb-6">
                <div className="flex flex-col">
                    <label className="text-sm font-medium mb-1 text-gray-700">Financial Year</label>
                    <select
                        value={financialYear}
                        onChange={(e) => setFinancialYear(e.target.value)}
                        className="border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-teal-500"
                    >
                        <option value="2022-23">2022-23</option>
                        <option value="2023-24">2023-24</option>
                        <option value="2024-25">2024-25</option>
                        <option value="2025-26">2025-26</option>
                        <option value="2026-27">2026-27</option>
                    </select>
                </div>

                <div className="flex flex-col">
                    <label className="text-sm font-medium mb-1 text-gray-700">Actual Line Loss (%)</label>
                    <div className="flex items-center gap-2">
                        <input
                            type="number"
                            step="0.01"
                            value={actualLoss}
                            onChange={(e) => setActualLoss(e.target.value)}
                            placeholder="e.g. 11.52"
                            className="border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-teal-500 w-32"
                        />
                        <button
                            onClick={handleEvaluate}
                            disabled={loading}
                            className="px-4 py-2 bg-teal-600 text-white rounded text-sm hover:bg-teal-700 disabled:opacity-50"
                        >
                            {loading ? 'Evaluating...' : 'Evaluate'}
                        </button>
                    </div>
                </div>
            </div>

            {result && (
                <div className={`p-4 rounded-lg border ${result.is_violation ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
                    <div className="flex items-start gap-3">
                        {result.is_violation ? (
                            <ExclamationTriangleIcon className="w-6 h-6 text-red-600 mt-1" />
                        ) : (
                            <CheckCircleIcon className="w-6 h-6 text-green-600 mt-1" />
                        )}

                        <div className="w-full">
                            <h3 className={`text-lg font-bold mb-2 ${result.is_violation ? 'text-red-800' : 'text-green-800'}`}>
                                {result.is_violation ? 'Efficiency Violation Detected' : 'Efficiency Target Achieved'}
                            </h3>

                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                <div>
                                    <p className="text-sm text-gray-600">Normative Target</p>
                                    <p className="text-lg font-medium">{result.target_loss_percent}%</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Actual Submission</p>
                                    <p className={`text-lg font-medium ${result.is_violation ? 'text-red-700' : 'text-green-700'}`}>
                                        {result.actual_loss_percent}%
                                    </p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Deviation</p>
                                    <p className="text-lg font-medium">
                                        {result.deviation_percent > 0 ? '+' : ''}{result.deviation_percent}%
                                    </p>
                                </div>
                                {result.is_violation && (
                                    <div>
                                        <p className="text-sm text-red-600 font-semibold">Est. Power Purchase Penalty</p>
                                        <p className="text-lg font-bold text-red-700">₹{result.penalty_estimate_cr} Cr</p>
                                    </div>
                                )}
                            </div>

                            <div className="text-sm bg-white bg-opacity-60 p-3 rounded">
                                <strong>Logic Engine:</strong> {result.logic_applied} <br />
                                <span className="text-gray-500 italic mt-1 inline-block">{result.regulatory_clause}</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
