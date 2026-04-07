import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { AuthService } from '../../services/api';
import { IS_DEMO_MODE, DEMO_CASE_ID } from '../../services/config';
import DemoModeBanner from '../common/DemoModeBanner';

// Types matching backend API
interface DecisionItem {
  ai_decision_id: string;
  deviation_report_id: string;
  sbu_code: string;
  cost_head: string;
  financial_year: string;
  petition_value: number;
  approved_value: number;
  actual_value?: number;
  variance_percent: number;
  ai_recommendation: 'APPROVE' | 'PARTIAL' | 'DISALLOW';
  confidence_score: number;
  decision_mode: 'AI_AUTO' | 'PENDING_MANUAL' | 'MANUAL_OVERRIDE';
  variance_exceeds_threshold: boolean;
  external_factor_detected: boolean;
  external_factor_category?: string;
  ai_justification: string;
  regulatory_clause: string;
  is_reviewed: boolean;
  officer_decision?: 'APPROVE' | 'PARTIAL' | 'DISALLOW';
}

interface WorkbenchData {
  sbu_code: string;
  total_items: number;
  pending_items: number;
  reviewed_items: number;
  completion_percent: number;
  pending_decisions: DecisionItem[];
  reviewed_decisions: DecisionItem[];
  external_factors_count: number;
  high_variance_count: number;
}

interface JustificationForm {
  ai_decision_id: string;
  officer_decision: 'APPROVE' | 'PARTIAL' | 'DISALLOW';
  final_value: number;
  justification_text: string;
  external_factor_category?: string;
  external_factor_description?: string;
  electricity_act_section?: string;
  kserc_regulation_ref?: string;
}

interface DocumentHistoryItem {
  document_id: string;
  version: string;
  mode: string;
  file_hash: string;
  file_size: number;
  generated_at: string;
  generated_by: string;
  download_count: number;
  is_finalized: boolean;
}

interface ToastNotification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

export const ManualDecisions: React.FC = () => {
  const { user } = useAuth();
  const token = AuthService.getToken();
  const [selectedSBU, setSelectedSBU] = useState<string>('SBU-D');
  const [workbench, setWorkbench] = useState<WorkbenchData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDecision, setSelectedDecision] = useState<DecisionItem | null>(null);
  const [formData, setFormData] = useState<JustificationForm | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  // PDF Generation Center state
  const [generatingPDF, setGeneratingPDF] = useState(false);
  const [documentHistory, setDocumentHistory] = useState<DocumentHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [modalMessage, setModalMessage] = useState('');
  
  // Case ID for PDF generation - using demo case ID in demo mode
  const [caseId, setCaseId] = useState<string>(IS_DEMO_MODE ? DEMO_CASE_ID : '');

  const SBUs = ['SBU-G', 'SBU-T', 'SBU-D'];

  useEffect(() => {
    fetchWorkbench();
  }, [selectedSBU]);

  const fetchWorkbench = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/justifications/workbench/${selectedSBU}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) throw new Error('Failed to fetch workbench data');
      
      const data = await response.json();
      setWorkbench(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleDecisionClick = (decision: DecisionItem) => {
    setSelectedDecision(decision);
    setFormData({
      ai_decision_id: decision.ai_decision_id,
      officer_decision: decision.officer_decision || decision.ai_recommendation,
      final_value: decision.actual_value || decision.approved_value,
      justification_text: '',
      external_factor_category: decision.external_factor_category,
      external_factor_description: '',
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData || !user) return;

    // Validation: justification required
    if (formData.officer_decision !== selectedDecision?.ai_recommendation) {
      if (!formData.justification_text || formData.justification_text.length < 50) {
        setError('Override justifications must be at least 50 characters');
        return;
      }
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/justifications', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          officer_value: formData.final_value,
        })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to submit decision');
      }

      const result = await response.json();
      
      // Refresh workbench
      await fetchWorkbench();
      
      // Navigate to next pending if available
      if (result.next_pending_decision) {
        const next = workbench?.pending_decisions.find(d => d.ai_decision_id === result.next_pending_decision);
        if (next) handleDecisionClick(next);
        else {
          setSelectedDecision(null);
          setFormData(null);
        }
      } else {
        setSelectedDecision(null);
        setFormData(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const getDecisionModeBadge = (mode: string) => {
    switch (mode) {
      case 'AI_AUTO':
        return <span className="badge badge-green">[A] AI Auto</span>;
      case 'PENDING_MANUAL':
        return <span className="badge badge-orange">[P] Pending</span>;
      case 'MANUAL_OVERRIDE':
        return <span className="badge badge-red">[M] Override</span>;
      default:
        return <span className="badge">{mode}</span>;
    }
  };

  // PDF Generation Center functions
  const addToast = (message: string, type: ToastNotification['type']) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  const fetchDocumentHistory = async () => {
    if (!caseId) return;
    
    setLoadingHistory(true);
    try {
      const response = await fetch(`/api/v1/cases/${caseId}/documents`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to fetch document history');
      }
      
      const data = await response.json();
      setDocumentHistory(data.documents || []);
    } catch (err) {
      console.error('Failed to fetch document history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const generatePDF = async (mode: 'DRAFT' | 'FINAL') => {
    if (!caseId) {
      addToast('Please enter a Case ID', 'error');
      return;
    }
    
    if (!workbench && !IS_DEMO_MODE) {
      addToast('Workbench data not loaded', 'error');
      return;
    }

    // DEMO MODE: Always force DRAFT mode, bypass pending check
    const actualMode = IS_DEMO_MODE ? 'DRAFT' : mode;
    
    // Check for pending decisions for FINAL mode (PRODUCTION only)
    if (!IS_DEMO_MODE && mode === 'FINAL' && (workbench?.pending_items || 0) > 0) {
      setModalMessage(`Manual decisions pending. Final document cannot be generated.\n\n${workbench?.pending_items} items require officer review before generating FINAL PDF.`);
      setShowModal(true);
      return;
    }

    setGeneratingPDF(true);
    try {
      const requestBody = {
        mode: actualMode
      };

      const response = await fetch(`/api/v1/cases/${caseId}/generate-pdf`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const err = await response.json();
        if (response.status === 409) {
          setModalMessage(`Cannot generate FINAL PDF: ${err.detail?.message || 'Pending decisions exist'}`);
          setShowModal(true);
        } else {
          throw new Error(err.detail || `Failed to generate ${mode} PDF`);
        }
        return;
      }

      const result = await response.json();
      addToast(`${actualMode} PDF generated successfully! Version: ${result.version}`, 'success');
      
      await fetchDocumentHistory();
      
      if (mode === 'DRAFT') {
        // Auto-download using the download URL
        window.open(result.download_url, '_blank');
      }
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'PDF generation failed', 'error');
    } finally {
      setGeneratingPDF(false);
    }
  };

  const downloadPDF = async (version: string) => {
    if (!caseId) return;
    
    try {
      const response = await fetch(`/api/v1/cases/${caseId}/download-pdf?version=${version}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to download PDF (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `KSERC_Order_${version}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      addToast('PDF downloaded successfully', 'success');
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Download failed', 'error');
    }
  };

  const downloadLatestPDF = async () => {
    if (!caseId) {
      addToast('Please enter a Case ID', 'error');
      return;
    }
    
    try {
      const response = await fetch(`/api/v1/cases/${caseId}/latest-pdf`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 404) {
          throw new Error('No PDF found for this case');
        }
        throw new Error(errorData.detail || `Failed to download PDF (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `KSERC_Order_Latest_${caseId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      addToast('Latest PDF downloaded successfully', 'success');
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Download failed', 'error');
    }
  };

  const dismissToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  return (
    <div className="manual-decisions-container">
      {/* Demo Mode Banner */}
      <DemoModeBanner />
      
      <div className="header-section">
        <h1>Manual Decisions Workbench</h1>
        <div className="sbu-selector">
          <label>Select SBU:</label>
          <select value={selectedSBU} onChange={(e) => setSelectedSBU(e.target.value)}>
            {SBUs.map(sbu => (
              <option key={sbu} value={sbu}>{sbu}</option>
            ))}
          </select>
        </div>
      </div>

      {workbench && (
        <div className="progress-bar-section">
          <div className="progress-info">
            <span>Progress: {workbench.completion_percent}%</span>
            <span>{workbench.reviewed_items} / {workbench.total_items} reviewed</span>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${workbench.completion_percent}%` }}
            />
          </div>
          <div className="stats-row">
            <span className="stat">
              <strong>{workbench.pending_items}</strong> Pending
            </span>
            <span className="stat">
              <strong>{workbench.external_factors_count}</strong> External Factors
            </span>
            <span className="stat">
              <strong>{workbench.high_variance_count}</strong> High Variance
            </span>
          </div>
        </div>
      )}

      {/* PDF Generation Center */}
      <div className="pdf-generation-center">
        <h2>PDF Generation Center</h2>
        
        {IS_DEMO_MODE && (
          <div className="demo-info-banner">
            <p> <strong>Demo Mode Active</strong></p>
            <p>Pre-loaded case: <code>{DEMO_CASE_ID}</code></p>
            <p>Click "Generate Demo PDF" to see the full workflow in action.</p>
          </div>
        )}
        
        <div className="case-input-section">
          <label>Case ID (PetitionData.id):</label>
          <input
            type="text"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            placeholder="Enter case UUID"
          />
          <button 
            className="btn-secondary"
            onClick={fetchDocumentHistory}
            disabled={!caseId || loadingHistory}
          >
            {loadingHistory ? 'Loading...' : 'Refresh History'}
          </button>
        </div>
        
        <div className="pdf-actions">
          <button 
            className="btn-draft"
            onClick={() => generatePDF('DRAFT')}
            disabled={generatingPDF || !caseId || (!workbench && !IS_DEMO_MODE)}
          >
            {generatingPDF ? 'Generating...' : (IS_DEMO_MODE ? '🎮 Generate Demo PDF' : '📄 Generate Draft PDF')}
          </button>
          
          <button 
            className="btn-final"
            onClick={() => generatePDF('FINAL')}
            disabled={generatingPDF || !caseId || IS_DEMO_MODE || (workbench?.pending_items || 0) > 0}
            title={IS_DEMO_MODE ? 'Final PDF not available in Demo Mode' : ((workbench?.pending_items || 0) > 0 ? 'Complete all pending decisions first' : '')}
          >
            {generatingPDF ? 'Generating...' : '📋 Generate Final PDF'}
          </button>
          
          <button 
            className="btn-secondary"
            onClick={downloadLatestPDF}
            disabled={!caseId || documentHistory.length === 0}
          >
            ⬇️ Download Latest
          </button>
        </div>
        
        {/* Demo Mode Info */}
        {IS_DEMO_MODE && (
          <div className="demo-info-panel">
            <h4>🎮 Demo Mode Features:</h4>
            <ul>
              <li>Pre-loaded sample case with realistic data</li>
              <li>Auto-generated AI decisions with justifications</li>
              <li>PDF generation always produces DRAFT with demo watermark</li>
              <li>No authentication required</li>
              <li>Full system workflow in one click</li>
            </ul>
          </div>
        )}
        
        {(workbench?.pending_items || 0) > 0 && !IS_DEMO_MODE && (
          <div className="pdf-warning">
            ⚠️ <strong>{workbench?.pending_items}</strong> pending decisions must be resolved before generating FINAL PDF
          </div>
        )}
        
        {documentHistory.length > 0 && (
          <div className="document-history">
            <h3>Document Version History</h3>
            <table className="history-table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Mode</th>
                  <th>Generated</th>
                  <th>By</th>
                  <th>Size</th>
                  <th>Downloads</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documentHistory.map((doc) => (
                  <tr key={doc.document_id} className={doc.is_finalized ? 'finalized' : ''}>
                    <td><strong>{doc.version}</strong></td>
                    <td>
                      <span className={`mode-badge ${doc.mode.toLowerCase()}`}>
                        {doc.mode}
                      </span>
                    </td>
                    <td>{new Date(doc.generated_at).toLocaleString()}</td>
                    <td>{doc.generated_by}</td>
                    <td>{(doc.file_size / 1024).toFixed(1)} KB</td>
                    <td>{doc.download_count}</td>
                    <td>
                      <button 
                        className="btn-small"
                        onClick={() => downloadPDF(doc.version)}
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal for pending items warning */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>⚠️ Cannot Generate Final PDF</h3>
            <p>{modalMessage}</p>
            <div className="modal-actions">
              <button 
                className="btn-secondary"
                onClick={() => setShowModal(false)}
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div 
            key={toast.id} 
            className={`toast toast-${toast.type}`}
            onClick={() => dismissToast(toast.id)}
          >
            {toast.message}
          </div>
        ))}
      </div>

      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠</span>
          {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div className="workbench-layout">
        <div className="decisions-list">
          <h3>Pending Decisions ({workbench?.pending_items || 0})</h3>
          {loading ? (
            <div className="loading">Loading decisions...</div>
          ) : workbench?.pending_decisions.length === 0 ? (
            <div className="empty-state">
              <p>🎉 All decisions reviewed!</p>
              {workbench?.reviewed_items > 0 && (
                <p>You can now generate the final order.</p>
              )}
            </div>
          ) : (
            <div className="decision-cards">
              {workbench?.pending_decisions.map((decision) => (
                <div 
                  key={decision.ai_decision_id}
                  className={`decision-card ${selectedDecision?.ai_decision_id === decision.ai_decision_id ? 'active' : ''}`}
                  onClick={() => handleDecisionClick(decision)}
                >
                  <div className="card-header">
                    <span className="cost-head">{decision.cost_head}</span>
                    {getDecisionModeBadge(decision.decision_mode)}
                  </div>
                  <div className="card-body">
                    <div className="value-row">
                      <span>Approved: ₹{decision.approved_value.toLocaleString()}</span>
                      {decision.actual_value && (
                        <span>Actual: ₹{decision.actual_value.toLocaleString()}</span>
                      )}
                    </div>
                    <div className="variance-row">
                      Variance: {decision.variance_percent.toFixed(1)}%
                      {decision.variance_exceeds_threshold && (
                        <span className="threshold-warning"> (Exceeds 25%)</span>
                      )}
                    </div>
                    <div className="ai-recommendation">
                      AI: {decision.ai_recommendation} ({(decision.confidence_score * 100).toFixed(0)}% confidence)
                    </div>
                    {decision.external_factor_detected && (
                      <div className="external-factor-badge">
                        ⚠ {decision.external_factor_category}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {workbench && workbench.reviewed_decisions.length > 0 && (
            <>
              <h3>Reviewed Decisions ({workbench.reviewed_items})</h3>
              <div className="decision-cards reviewed">
                {workbench.reviewed_decisions.map((decision) => (
                  <div key={decision.ai_decision_id} className="decision-card reviewed-card">
                    <div className="card-header">
                      <span className="cost-head">{decision.cost_head}</span>
                      <span className="badge badge-green">✓ Reviewed</span>
                    </div>
                    <div className="card-body">
                      <div className="final-decision">
                        Final: <strong>{decision.officer_decision}</strong>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {selectedDecision && formData && (
          <div className="decision-form-panel">
            <h3>Review Decision</h3>
            <div className="ai-info">
              <h4>AI Analysis</h4>
              <p><strong>Cost Head:</strong> {selectedDecision.cost_head}</p>
              <p><strong>Recommendation:</strong> {selectedDecision.ai_recommendation}</p>
              <p><strong>Confidence:</strong> {(selectedDecision.confidence_score * 100).toFixed(1)}%</p>
              <p><strong>Justification:</strong> {selectedDecision.ai_justification}</p>
              <p><strong>Regulatory Basis:</strong> {selectedDecision.regulatory_clause}</p>
            </div>

            <form onSubmit={handleSubmit} className="justification-form">
              <h4>Officer Decision</h4>
              
              <div className="form-group">
                <label>Final Decision *</label>
                <select 
                  value={formData.officer_decision}
                  onChange={(e) => setFormData({...formData, officer_decision: e.target.value as any})}
                >
                  <option value="APPROVE">APPROVE</option>
                  <option value="PARTIAL">PARTIAL</option>
                  <option value="DISALLOW">DISALLOW</option>
                </select>
              </div>

              <div className="form-group">
                <label>Approved Value (₹) *</label>
                <input 
                  type="number"
                  value={formData.final_value}
                  onChange={(e) => setFormData({...formData, final_value: parseFloat(e.target.value)})}
                  step="0.01"
                />
              </div>

              <div className="form-group">
                <label>
                  Justification Text *
                  {formData.officer_decision !== selectedDecision.ai_recommendation && (
                    <span className="required-note"> (Required for override, min 50 chars)</span>
                  )}
                </label>
                <textarea
                  value={formData.justification_text}
                  onChange={(e) => setFormData({...formData, justification_text: e.target.value})}
                  rows={6}
                  placeholder="Provide detailed justification for your decision..."
                  minLength={20}
                  required
                />
                <small>{formData.justification_text.length} characters</small>
              </div>

              <div className="form-group">
                <label>External Factor (if applicable)</label>
                <select
                  value={formData.external_factor_category || ''}
                  onChange={(e) => setFormData({...formData, external_factor_category: e.target.value || undefined})}
                >
                  <option value="">None</option>
                  <option value="Hydrology">Hydrology</option>
                  <option value="Power_Purchase_Volatility">Power Purchase Volatility</option>
                  <option value="Government_Mandate">Government Mandate</option>
                  <option value="Court_Order">Court Order</option>
                  <option value="CapEx_Overrun">CapEx Overrun</option>
                  <option value="Force_Majeure">Force Majeure</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              {formData.external_factor_category && (
                <div className="form-group">
                  <label>External Factor Description</label>
                  <textarea
                    value={formData.external_factor_description}
                    onChange={(e) => setFormData({...formData, external_factor_description: e.target.value})}
                    rows={3}
                    placeholder="Describe the external factor..."
                  />
                </div>
              )}

              <div className="form-group">
                <label>Electricity Act Section</label>
                <input
                  type="text"
                  value={formData.electricity_act_section || ''}
                  onChange={(e) => setFormData({...formData, electricity_act_section: e.target.value})}
                  placeholder="e.g., Section 61, 62"
                />
              </div>

              <div className="form-group">
                <label>KSERC Regulation Reference</label>
                <input
                  type="text"
                  value={formData.kserc_regulation_ref || ''}
                  onChange={(e) => setFormData({...formData, kserc_regulation_ref: e.target.value})}
                  placeholder="e.g., Regulation 9.2"
                />
              </div>

              <div className="form-actions">
                <button 
                  type="button" 
                  className="btn-secondary"
                  onClick={() => { setSelectedDecision(null); setFormData(null); }}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn-primary"
                  disabled={submitting}
                >
                  {submitting ? 'Submitting...' : 'Submit Decision'}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      <style>{`
        .manual-decisions-container {
          padding: 20px;
          max-width: 1400px;
          margin: 0 auto;
        }

        .header-section {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .header-section h1 {
          margin: 0;
          font-size: 24px;
        }

        .sbu-selector {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .sbu-selector select {
          padding: 8px 12px;
          border: 1px solid #ccc;
          border-radius: 4px;
          font-size: 14px;
        }

        .progress-bar-section {
          background: #f5f5f5;
          padding: 15px 20px;
          border-radius: 8px;
          margin-bottom: 20px;
        }

        .progress-info {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
          font-weight: 500;
        }

        .progress-bar {
          height: 8px;
          background: #ddd;
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 10px;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #4CAF50, #8BC34A);
          transition: width 0.3s ease;
        }

        .stats-row {
          display: flex;
          gap: 20px;
          font-size: 14px;
        }

        .stat strong {
          color: #333;
        }

        .error-banner {
          background: #FFEBEE;
          border: 1px solid #EF5350;
          padding: 12px 15px;
          border-radius: 4px;
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 20px;
        }

        .error-icon {
          font-size: 18px;
        }

        .error-banner button {
          margin-left: auto;
          background: none;
          border: none;
          color: #C62828;
          cursor: pointer;
        }

        .workbench-layout {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }

        .decisions-list h3 {
          margin: 0 0 15px 0;
          font-size: 16px;
          color: #555;
        }

        .decision-cards {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .decision-card {
          background: white;
          border: 1px solid #ddd;
          border-radius: 6px;
          padding: 15px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .decision-card:hover {
          border-color: #2196F3;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .decision-card.active {
          border-color: #2196F3;
          background: #E3F2FD;
        }

        .reviewed-card {
          opacity: 0.7;
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }

        .cost-head {
          font-weight: 600;
          font-size: 14px;
        }

        .badge {
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 500;
        }

        .badge-green {
          background: #E8F5E9;
          color: #2E7D32;
        }

        .badge-orange {
          background: #FFF3E0;
          color: #EF6C00;
        }

        .badge-red {
          background: #FFEBEE;
          color: #C62828;
        }

        .card-body {
          font-size: 13px;
          color: #666;
        }

        .value-row {
          display: flex;
          gap: 15px;
          margin-bottom: 5px;
        }

        .variance-row {
          margin-bottom: 5px;
        }

        .threshold-warning {
          color: #C62828;
          font-weight: 500;
        }

        .ai-recommendation {
          color: #555;
        }

        .external-factor-badge {
          background: #FFF8E1;
          color: #F57C00;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          margin-top: 8px;
          display: inline-block;
        }

        .decision-form-panel {
          background: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 20px;
          position: sticky;
          top: 20px;
          max-height: calc(100vh - 100px);
          overflow-y: auto;
        }

        .decision-form-panel h3 {
          margin: 0 0 15px 0;
          font-size: 18px;
        }

        .ai-info {
          background: #f5f5f5;
          padding: 15px;
          border-radius: 6px;
          margin-bottom: 20px;
        }

        .ai-info h4 {
          margin: 0 0 10px 0;
          font-size: 14px;
          color: #555;
        }

        .ai-info p {
          margin: 5px 0;
          font-size: 13px;
        }

        .justification-form {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .justification-form h4 {
          margin: 0;
          font-size: 14px;
          color: #555;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 5px;
        }

        .form-group label {
          font-size: 13px;
          font-weight: 500;
        }

        .required-note {
          color: #C62828;
          font-weight: normal;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
          padding: 8px 12px;
          border: 1px solid #ccc;
          border-radius: 4px;
          font-size: 14px;
        }

        .form-group textarea {
          resize: vertical;
          font-family: inherit;
        }

        .form-group small {
          color: #999;
          font-size: 11px;
        }

        .form-actions {
          display: flex;
          gap: 10px;
          margin-top: 10px;
        }

        .btn-secondary {
          padding: 10px 20px;
          border: 1px solid #ccc;
          background: white;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        }

        .btn-primary {
          padding: 10px 20px;
          border: none;
          background: #2196F3;
          color: white;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        }

        .btn-primary:disabled {
          background: #90CAF9;
          cursor: not-allowed;
        }

        .loading {
          text-align: center;
          padding: 40px;
          color: #666;
        }

        .empty-state {
          text-align: center;
          padding: 40px;
          color: #666;
        }

        .empty-state p {
          margin: 10px 0;
        }

        /* PDF Generation Center Styles */
        .pdf-generation-center {
          background: #f8f9fa;
          border: 1px solid #dee2e6;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 20px;
        }

        .pdf-generation-center h2 {
          margin: 0 0 15px 0;
          font-size: 18px;
          color: #333;
        }

        .case-input-section {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 15px;
          flex-wrap: wrap;
        }

        .case-input-section label {
          font-weight: 500;
          color: #555;
        }

        .case-input-section input {
          flex: 1;
          min-width: 200px;
          padding: 8px 12px;
          border: 1px solid #ccc;
          border-radius: 4px;
          font-size: 14px;
        }

        .pdf-actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-bottom: 15px;
        }

        .btn-draft {
          padding: 12px 24px;
          border: none;
          background: #FF9800;
          color: white;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
        }

        .btn-draft:hover:not(:disabled) {
          background: #F57C00;
        }

        .btn-draft:disabled {
          background: #FFE0B2;
          cursor: not-allowed;
        }

        .btn-final {
          padding: 12px 24px;
          border: none;
          background: #4CAF50;
          color: white;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
        }

        .btn-final:hover:not(:disabled) {
          background: #388E3C;
        }

        .btn-final:disabled {
          background: #C8E6C9;
          cursor: not-allowed;
        }

        .pdf-warning {
          background: #FFF3E0;
          border: 1px solid #FFB74D;
          color: #E65100;
          padding: 10px 15px;
          border-radius: 4px;
          margin-bottom: 15px;
          font-size: 13px;
        }

        .document-history {
          margin-top: 20px;
        }

        .document-history h3 {
          margin: 0 0 10px 0;
          font-size: 14px;
          color: #555;
        }

        .history-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }

        .history-table th,
        .history-table td {
          border: 1px solid #ddd;
          padding: 8px;
          text-align: left;
        }

        .history-table th {
          background: #f0f0f0;
          font-weight: 600;
        }

        .history-table tr.finalized {
          background: #E8F5E9;
        }

        .mode-badge {
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 500;
        }

        .mode-badge.draft {
          background: #FFF3E0;
          color: #EF6C00;
        }

        .mode-badge.final {
          background: #E8F5E9;
          color: #2E7D32;
        }

        .btn-small {
          padding: 4px 8px;
          border: 1px solid #2196F3;
          background: white;
          color: #2196F3;
          border-radius: 3px;
          cursor: pointer;
          font-size: 11px;
        }

        .btn-small:hover {
          background: #2196F3;
          color: white;
        }

        /* Toast Notifications */
        .toast-container {
          position: fixed;
          top: 20px;
          right: 20px;
          z-index: 1000;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .toast {
          padding: 12px 20px;
          border-radius: 4px;
          color: white;
          font-size: 14px;
          cursor: pointer;
          box-shadow: 0 2px 5px rgba(0,0,0,0.2);
          min-width: 250px;
          animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        .toast-success {
          background: #4CAF50;
        }

        .toast-error {
          background: #F44336;
        }

        .toast-info {
          background: #2196F3;
        }

        /* Modal Styles */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1001;
        }

        .modal-content {
          background: white;
          border-radius: 8px;
          padding: 30px;
          max-width: 500px;
          width: 90%;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .modal-content h3 {
          margin: 0 0 15px 0;
          color: #E65100;
          font-size: 18px;
        }

        .modal-content p {
          margin: 0 0 20px 0;
          line-height: 1.5;
          color: #333;
          white-space: pre-line;
        }

        .modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
        }

        /* Demo Mode Styles */
        .demo-info-banner {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 15px 20px;
          border-radius: 8px;
          margin-bottom: 20px;
          font-size: 14px;
        }

        .demo-info-banner p {
          margin: 5px 0;
        }

        .demo-info-banner code {
          background: rgba(255, 255, 255, 0.2);
          padding: 2px 6px;
          border-radius: 3px;
          font-family: monospace;
        }

        .demo-info-panel {
          background: #f0f4ff;
          border: 2px dashed #6366f1;
          border-radius: 8px;
          padding: 20px;
          margin: 15px 0;
        }

        .demo-info-panel h4 {
          margin: 0 0 10px 0;
          color: #4f46e5;
        }

        .demo-info-panel ul {
          margin: 0;
          padding-left: 20px;
          color: #4338ca;
        }

        .demo-info-panel li {
          margin: 5px 0;
        }
      `}</style>
    </div>
  );
};
