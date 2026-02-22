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
      const data = await ReportsService.generateAnalyticalReport(
        financialYear,
        selectedSBU || undefined
      );
      setReport(data);
      toast.success('Report generated successfully');
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Analytical Reports</h2>

      <div className="flex gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium mb-1">Financial Year</label>
          <select
            value={financialYear}
            onChange={(e) => setFinancialYear(e.target.value)}
            className="border rounded px-3 py-2"
          >
            <option value="2022-23">2022-23</option>
            <option value="2023-24">2023-24</option>
            <option value="2024-25">2024-25</option>
            <option value="2025-26">2025-26</option>
            <option value="2026-27">2026-27</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">SBU (Optional)</label>
          <select
            value={selectedSBU}
            onChange={(e) => setSelectedSBU(e.target.value as SBUCode | '')}
            className="border rounded px-3 py-2"
          >
            <option value="">All SBUs</option>
            <option value={SBUCode.SBU_GENERATION}>Generation (SBU-G)</option>
            <option value={SBUCode.SBU_TRANSMISSION}>Transmission (SBU-T)</option>
            <option value={SBUCode.SBU_DISTRIBUTION}>Distribution (SBU-D)</option>
          </select>
        </div>

        <div className="flex items-end">
          <button
            onClick={generateReport}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate Report'}
          </button>
        </div>
      </div>

      {report && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-500">Approved ARR</p>
              <p className="text-xl font-bold">₹{(report.preliminary_summary.total_approved_arr / 1e7).toFixed(2)} Cr</p>
            </div>
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-500">Actual ARR</p>
              <p className="text-xl font-bold">₹{(report.preliminary_summary.total_actual_arr / 1e7).toFixed(2)} Cr</p>
            </div>
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-500">Net Variance</p>
              <p className={`text-xl font-bold ${report.preliminary_summary.net_variance < 0 ? 'text-red-500' : 'text-green-500'}`}>
                ₹{(report.preliminary_summary.net_variance / 1e7).toFixed(2)} Cr
              </p>
            </div>
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-500">Anomalies</p>
              <p className="text-xl font-bold">{report.anomaly_count}</p>
            </div>
          </div>

          {/* AI Insights */}
          {report.insights.length > 0 && (
            <div className="bg-blue-50 p-4 rounded">
              <h3 className="font-semibold mb-2">AI Insights</h3>
              <ul className="list-disc list-inside space-y-1">
                {report.insights.map((insight, idx) => (
                  <li key={idx} className="text-sm text-gray-700">{insight}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {report.recommendations.length > 0 && (
            <div className="bg-yellow-50 p-4 rounded">
              <h3 className="font-semibold mb-2">Regulatory Recommendations</h3>
              <ul className="list-disc list-inside space-y-1">
                {report.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-sm text-gray-700">{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Tariff Draft Generation Card */}
          <TariffDraft report={report} />

          {/* Report Metadata */}
          <div className="text-xs text-gray-400">
            Report ID: {report.report_id} | Checksum: {report.checksum.substring(0, 16)}... | Generated: {new Date(report.generated_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}
