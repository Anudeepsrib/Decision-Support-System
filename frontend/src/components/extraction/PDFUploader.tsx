import React, { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { ExtractionService } from '../../services/api';
import { ExtractionResponse } from '../../services/types';

interface PDFUploaderProps {
  onUploadComplete: (response: ExtractionResponse) => void;
}

export function PDFUploader({ onUploadComplete }: PDFUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [results, setResults] = useState<ExtractionResponse | null>(null);

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Please upload a PDF file');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      toast.error('File size must be less than 50MB');
      return;
    }
    setUploading(true);
    setResults(null);
    try {
      const response = await ExtractionService.uploadPDF(file);
      toast.success(`Extracted ${response.total_fields_extracted} fields from ${response.total_pages_processed} pages`);
      setResults(response);
      onUploadComplete(response);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [onUploadComplete]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) handleFile(e.target.files[0]);
  };

  return (
    <div>
      <h2 style={styles.pageTitle}>Upload Document</h2>
      <p style={styles.pageDesc}>Upload PDF petitions and audited financials for AI-powered data extraction.</p>

      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        style={{
          ...styles.dropzone,
          ...(dragActive ? styles.dropzoneActive : {}),
          ...(uploading ? styles.dropzoneDisabled : {}),
        }}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileInput}
          style={{ display: 'none' }}
          id="file-upload"
          disabled={uploading}
        />
        <label htmlFor="file-upload" style={{ ...styles.dropLabel, ...(uploading ? { cursor: 'default' } : {}) }}>
          <div style={styles.uploadIcon}>
            {uploading ? (
              <div style={styles.spinnerContainer}>
                <div style={styles.spinner} />
              </div>
            ) : (
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect width="48" height="48" rx="12" fill={dragActive ? '#ebf8ff' : '#f7fafc'} />
                <path d="M24 16v16M16 24l8-8 8 8" stroke={dragActive ? '#3182ce' : '#a0aec0'} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </div>

          {uploading ? (
            <>
              <p style={styles.dropText}>Extracting data with AI...</p>
              <p style={styles.loadingHint}>
                ⏳ Large documents (100+ pages) may take 2–3 minutes. Please keep this tab open.
              </p>
            </>
          ) : dragActive ? (
            <p style={{ ...styles.dropText, color: '#3182ce' }}>Drop the PDF here...</p>
          ) : (
            <>
              <p style={styles.dropText}>Drag &amp; drop a PDF file here, or <span style={styles.browseLink}>click to browse</span></p>
              <p style={styles.dropHint}>Supports: PDF files up to 50MB</p>
            </>
          )}
        </label>
      </div>

      {/* Extraction Results Panel */}
      {results && !uploading && (
        <div style={styles.resultsPanel}>
          <div style={styles.resultsHeader}>
            <span style={styles.resultsIcon}>✅</span>
            <h3 style={styles.resultsTitle}>Extraction Complete!</h3>
          </div>
          <p style={styles.resultsSummary}>
            <strong>{results.filename}</strong> — processed {results.total_pages_processed} pages
          </p>

          <div style={styles.statsRow}>
            <div style={styles.statBox}>
              <span style={styles.statValue}>{results.total_fields_extracted}</span>
              <span style={styles.statLabel}>Fields Extracted</span>
            </div>
            <div style={styles.statBox}>
              <span style={styles.statValue}>{results.fields_requiring_review}</span>
              <span style={styles.statLabel}>Need Review</span>
            </div>
            <div style={styles.statBox}>
              <span style={styles.statValue}>{results.total_pages_processed}</span>
              <span style={styles.statLabel}>Pages Scanned</span>
            </div>
          </div>

          {/* Top extracted fields preview */}
          {results.fields && results.fields.length > 0 && (
            <div style={styles.fieldsPreview}>
              <h4 style={styles.fieldsPreviewTitle}>Extracted Fields Preview</h4>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Field</th>
                    <th style={styles.th}>SBU</th>
                    <th style={styles.th}>Value</th>
                    <th style={styles.th}>Confidence</th>
                    <th style={styles.th}>Page</th>
                  </tr>
                </thead>
                <tbody>
                  {results.fields.slice(0, 8).map((field, idx) => {
                    const conf = Math.round(field.confidence_score * 100);
                    const confColor = conf >= 80 ? '#38a169' : conf >= 60 ? '#d69e2e' : '#e53e3e';
                    return (
                      <tr key={idx} style={idx % 2 === 0 ? styles.trEven : styles.trOdd}>
                        <td style={styles.td}>{field.field_name}</td>
                        <td style={styles.td}><span style={styles.sbuBadge}>{field.sbu_code}</span></td>
                        <td style={styles.td}>
                          {field.extracted_value !== null
                            ? `₹${field.extracted_value.toLocaleString('en-IN')}`
                            : <span style={{ color: '#a0aec0' }}>N/A</span>}
                        </td>
                        <td style={styles.td}>
                          <span style={{ ...styles.confBadge, color: confColor, borderColor: confColor }}>
                            {conf}%
                          </span>
                        </td>
                        <td style={styles.td}>p.{field.source_page}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {results.fields.length > 8 && (
                <p style={styles.moreFields}>+{results.fields.length - 8} more fields in Mapping Workbench</p>
              )}
            </div>
          )}

          <Link to="/mapping" style={styles.workbenchBtn}>
            🔗 Review in Mapping Workbench →
          </Link>
        </div>
      )}

      <div style={styles.infoCard}>
        <h3 style={styles.infoTitle}>What happens next?</h3>
        <div style={styles.stepsList}>
          <div style={styles.step}><span style={styles.stepNum}>1</span> AI scans all pages and detects financial tables</div>
          <div style={styles.step}><span style={styles.stepNum}>2</span> Financial figures are extracted with confidence scores</div>
          <div style={styles.step}><span style={styles.stepNum}>3</span> Results are sent to the Mapping Workbench for your review</div>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  pageTitle: { fontSize: '1.35rem', fontWeight: 600, color: '#1a365d', margin: '0 0 0.5rem' },
  pageDesc: { fontSize: '0.9rem', color: '#718096', margin: '0 0 1.5rem' },
  dropzone: {
    border: '2px dashed #cbd5e0', borderRadius: '16px', padding: '3rem 2rem',
    textAlign: 'center' as const, cursor: 'pointer', transition: 'all 0.3s ease',
    background: '#fafbfc', marginBottom: '1.5rem',
  },
  dropzoneActive: { borderColor: '#3182ce', background: '#ebf8ff' },
  dropzoneDisabled: { cursor: 'default', opacity: 0.85, background: '#f0f4f8' },
  dropLabel: { cursor: 'pointer', display: 'block' },
  uploadIcon: { marginBottom: '1rem', display: 'flex', justifyContent: 'center' },
  spinnerContainer: { display: 'flex', justifyContent: 'center' },
  spinner: {
    width: '40px', height: '40px', border: '3px solid #e2e8f0',
    borderTopColor: '#3182ce', borderRadius: '50%', animation: 'spin 0.8s linear infinite',
  },
  dropText: { fontSize: '0.95rem', color: '#4a5568', margin: '0 0 0.5rem' },
  browseLink: { color: '#3182ce', fontWeight: 600, textDecoration: 'underline' },
  dropHint: { fontSize: '0.8rem', color: '#a0aec0', margin: 0 },
  loadingHint: { fontSize: '0.8rem', color: '#718096', margin: '0.4rem 0 0', fontStyle: 'italic' },
  // Results Panel
  resultsPanel: {
    background: '#f0fff4', border: '1.5px solid #9ae6b4', borderRadius: '16px',
    padding: '1.5rem', marginBottom: '1.5rem',
  },
  resultsHeader: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' },
  resultsIcon: { fontSize: '1.3rem' },
  resultsTitle: { fontSize: '1.1rem', fontWeight: 700, color: '#22543d', margin: 0 },
  resultsSummary: { fontSize: '0.88rem', color: '#4a5568', margin: '0 0 1rem' },
  statsRow: { display: 'flex', gap: '1rem', marginBottom: '1.25rem', flexWrap: 'wrap' as const },
  statBox: {
    flex: 1, minWidth: '100px', background: '#fff', borderRadius: '10px',
    padding: '0.85rem 1rem', textAlign: 'center' as const,
    border: '1px solid #c6f6d5', display: 'flex', flexDirection: 'column' as const, gap: '0.2rem',
  },
  statValue: { fontSize: '1.6rem', fontWeight: 800, color: '#276749' },
  statLabel: { fontSize: '0.72rem', color: '#718096', textTransform: 'uppercase' as const, letterSpacing: '0.04em' },
  fieldsPreview: { marginBottom: '1.25rem' },
  fieldsPreviewTitle: { fontSize: '0.88rem', fontWeight: 600, color: '#2d3748', margin: '0 0 0.5rem' },
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '0.8rem' },
  th: {
    textAlign: 'left' as const, padding: '0.45rem 0.6rem',
    background: '#e6fffa', color: '#285e61', fontSize: '0.72rem',
    fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: '0.03em',
    borderBottom: '1.5px solid #b2f5ea',
  },
  td: { padding: '0.4rem 0.6rem', color: '#4a5568', borderBottom: '1px solid #f0fff4' },
  trEven: { background: '#fff' },
  trOdd: { background: '#f0fff4' },
  sbuBadge: {
    background: '#ebf8ff', color: '#2b6cb0', padding: '0.1rem 0.4rem',
    borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600,
  },
  confBadge: {
    border: '1px solid', borderRadius: '4px', padding: '0.1rem 0.4rem',
    fontSize: '0.72rem', fontWeight: 700, background: 'transparent',
  },
  moreFields: { fontSize: '0.76rem', color: '#718096', textAlign: 'center' as const, margin: '0.5rem 0 0', fontStyle: 'italic' },
  workbenchBtn: {
    display: 'inline-block', background: 'linear-gradient(135deg, #276749 0%, #38a169 100%)',
    color: '#fff', padding: '0.65rem 1.5rem', borderRadius: '10px',
    textDecoration: 'none', fontWeight: 700, fontSize: '0.88rem',
    boxShadow: '0 2px 8px rgba(56,161,105,0.3)',
  },
  // Info Card
  infoCard: {
    background: '#fff', borderRadius: '12px', padding: '1.25rem',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)', border: '1px solid #edf2f7',
  },
  infoTitle: { fontSize: '0.95rem', fontWeight: 600, color: '#2d3748', margin: '0 0 0.75rem' },
  stepsList: { display: 'flex', flexDirection: 'column' as const, gap: '0.6rem' },
  step: { display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.85rem', color: '#4a5568' },
  stepNum: {
    width: '24px', height: '24px', borderRadius: '50%', background: '#ebf8ff',
    color: '#3182ce', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    fontSize: '0.75rem', fontWeight: 700, flexShrink: 0,
  },
};
