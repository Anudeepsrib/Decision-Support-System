import React, { useCallback, useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { ExtractionService } from '../../services/api';
import { ExtractionResponse } from '../../services/types';

interface PDFUploaderProps {
  onUploadComplete: (response: ExtractionResponse) => void;
}

// Live step definitions — timestamps are soft targets (auto-advance)
const STEPS = [
  { icon: '📤', label: 'Uploading file to server', advanceAfter: 0 },
  { icon: '🔍', label: 'Reading PDF pages', advanceAfter: 4000 },
  { icon: '🤖', label: 'Running AI extraction pipeline', advanceAfter: 12000 },
  { icon: '🗺️', label: 'Auto-mapping to regulatory heads', advanceAfter: 55000 },
  { icon: '✅', label: 'Finalising results', advanceAfter: 110000 },
];

export function PDFUploader({ onUploadComplete }: PDFUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [results, setResults] = useState<ExtractionResponse | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);       // seconds
  const stepTimers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const elapsedTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clear all timers
  const clearTimers = () => {
    stepTimers.current.forEach(clearTimeout);
    stepTimers.current = [];
    if (elapsedTimer.current) clearInterval(elapsedTimer.current);
  };

  // Start step auto-advance timers
  const startStepTimers = () => {
    setCurrentStep(0);
    setElapsed(0);

    // Elapsed counter
    elapsedTimer.current = setInterval(() => setElapsed((s) => s + 1), 1000);

    // Schedule each step advance
    STEPS.forEach((step, idx) => {
      if (idx === 0) return; // step 0 starts immediately
      const t = setTimeout(() => setCurrentStep(idx), step.advanceAfter);
      stepTimers.current.push(t);
    });
  };

  useEffect(() => () => clearTimers(), []);

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Please upload a PDF file'); return;
    }
    if (file.size > 50 * 1024 * 1024) {
      toast.error('File size must be less than 50MB'); return;
    }

    setUploading(true);
    setResults(null);
    startStepTimers();

    try {
      const response = await ExtractionService.uploadPDF(file);
      clearTimers();
      setCurrentStep(STEPS.length); // mark all done
      toast.success(`✅ Extracted ${response.total_fields_extracted} fields from ${response.total_pages_processed} pages`);
      setResults(response);
      onUploadComplete(response);
    } catch (error) {
      clearTimers();
      toast.error(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [onUploadComplete]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFile(e.target.files[0]);
  };

  const fmtElapsed = (s: number) => s < 60
    ? `${s}s`
    : `${Math.floor(s / 60)}m ${s % 60}s`;

  const done = currentStep >= STEPS.length;

  return (
    <div className="slideUp">
      <div style={s.pageHeader}>
        <h2 style={s.pageTitle}>Upload Document</h2>
        <p style={s.pageDesc}>
          Upload PDF petitions and audited financials for AI-powered data extraction.
          Large documents may take 2–3 minutes.
        </p>
      </div>

      {/* ── Drop Zone ── */}
      {!uploading && !results && (
        <div
          onDragEnter={handleDrag} onDragOver={handleDrag}
          onDragLeave={handleDrag} onDrop={handleDrop}
          style={{ ...s.dropzone, ...(dragActive ? s.dropzoneActive : {}) }}
        >
          <input type="file" accept=".pdf" onChange={handleFileInput}
            style={{ display: 'none' }} id="file-upload" />
          <label htmlFor="file-upload" style={s.dropLabel}>
            <div style={{ ...s.dropIconWrap, ...(dragActive ? s.dropIconWrapActive : {}) }}>
              {dragActive
                ? <span style={{ fontSize: '2.5rem' }}>📂</span>
                : <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                  <circle cx="20" cy="20" r="20" fill="rgba(49,130,206,0.08)" />
                  <path d="M20 13v14M13 20l7-7 7 7" stroke="#3182ce" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              }
            </div>
            <p style={s.dropMain}>
              {dragActive
                ? <span style={{ color: '#3182ce', fontWeight: 700 }}>Release to upload</span>
                : <><strong>Drag & drop</strong> your PDF here, or <span style={s.browse}>click to browse</ span></>
              }
            </p>
            <p style={s.dropHint}>PDF files • Max 50 MB</p>
          </label>
        </div>
      )}

      {/* ── Live Progress Timeline ── */}
      {uploading && (
        <div style={s.progressCard}>
          <div style={s.progressHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={s.spinnerLg} />
              <div>
                <p style={s.progressTitle}>Processing Document...</p>
                <p style={s.progressSub}>Keep this tab open · {fmtElapsed(elapsed)} elapsed</p>
              </div>
            </div>
          </div>

          {/* Step timeline */}
          <div style={s.timeline}>
            {STEPS.map((step, idx) => {
              const isActive = idx === currentStep;
              const isCompleted = idx < currentStep;
              const isPending = idx > currentStep;
              return (
                <div key={idx} style={s.timelineRow}>
                  {/* Connector */}
                  {idx > 0 && (
                    <div style={{
                      ...s.connector,
                      background: isCompleted || isActive ? '#3182ce' : '#e2e8f0',
                    }} />
                  )}
                  {/* Node */}
                  <div style={{
                    ...s.stepNode,
                    ...(isCompleted ? s.stepNodeDone : isActive ? s.stepNodeActive : s.stepNodePending),
                  }}>
                    {isCompleted
                      ? <span style={{ fontSize: '0.75rem' }}>✓</span>
                      : isActive
                        ? <span style={s.stepSpinner} />
                        : <span style={{ fontSize: '0.65rem', opacity: 0.4 }}>{idx + 1}</span>
                    }
                  </div>
                  {/* Label */}
                  <div style={{
                    ...s.stepLabel,
                    ...(isCompleted ? s.stepLabelDone : isActive ? s.stepLabelActive : s.stepLabelPending),
                  }}>
                    {step.icon} {step.label}
                    {isActive && <span style={s.stepBlink}>...</span>}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Note */}
          <div style={s.progressNote}>
            ⏳ Large PDFs (100+ pages) require 2–3 minutes for thorough AI extraction.
            Results will appear automatically when done.
          </div>
        </div>
      )}

      {/* ── Extraction Results Panel ── */}
      {results && !uploading && (
        <div style={s.resultsCard} className="slideUp">
          <div style={s.resultsHeaderRow}>
            <div>
              <p style={s.resultsTitle}>✅ Extraction Complete</p>
              <p style={s.resultsFile}>{results.filename}</p>
            </div>
            <button
              onClick={() => { setResults(null); }}
              style={s.uploadAgainBtn}
            >
              Upload Another
            </button>
          </div>

          {/* Stats */}
          <div style={s.statsGrid}>
            {[
              { value: results.total_fields_extracted, label: 'Fields Extracted', color: '#276749' },
              { value: results.total_pages_processed, label: 'Pages Scanned', color: '#2c5282' },
              { value: results.fields_requiring_review, label: 'Need Review', color: results.fields_requiring_review > 0 ? '#d69e2e' : '#276749' },
            ].map((stat) => (
              <div key={stat.label} style={s.statBox}>
                <span style={{ ...s.statVal, color: stat.color }}>{stat.value}</span>
                <span style={s.statLbl}>{stat.label}</span>
              </div>
            ))}
          </div>

          {/* Fields preview table */}
          {results.fields?.length > 0 && (
            <div style={s.tableWrap}>
              <p style={s.tableTitle}>Extracted Fields Preview</p>
              <table style={s.table}>
                <thead>
                  <tr>
                    <th style={s.th}>Field</th>
                    <th style={s.th}>SBU</th>
                    <th style={s.th}>Value (₹)</th>
                    <th style={s.th}>Confidence</th>
                    <th style={s.th}>Page</th>
                  </tr>
                </thead>
                <tbody>
                  {results.fields.slice(0, 10).map((f, i) => {
                    const pct = Math.round(f.confidence_score * 100);
                    const confColor = pct >= 80 ? '#276749' : pct >= 55 ? '#b45309' : '#c53030';
                    return (
                      <tr key={i} style={{ background: i % 2 ? '#f8fafc' : '#fff' }}>
                        <td style={s.td}>{f.field_name}</td>
                        <td style={s.td}>
                          <span style={{ ...s.sbuPill, background: '#ebf8ff', color: '#2c5282' }}>
                            {f.sbu_code}
                          </span>
                        </td>
                        <td style={s.td}>
                          {f.extracted_value !== null
                            ? `₹${f.extracted_value.toLocaleString('en-IN')}`
                            : <span style={{ color: '#a0aec0' }}>N/A</span>}
                        </td>
                        <td style={s.td}>
                          <div style={s.confBar}>
                            <div style={{ ...s.confFill, width: `${pct}%`, background: confColor }} />
                            <span style={{ ...s.confLabel, color: confColor }}>{pct}%</span>
                          </div>
                        </td>
                        <td style={s.td}>p.{f.source_page}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {results.fields.length > 10 && (
                <p style={s.moreNote}>+{results.fields.length - 10} more fields available in the Mapping Workbench</p>
              )}
            </div>
          )}

          <Link to="/mapping" style={s.workbenchBtn}>
            🔗 Review in Mapping Workbench →
          </Link>
        </div>
      )}

      {/* ── Info Steps (shown when idle) ── */}
      {!uploading && !results && (
        <div style={s.infoCard}>
          <p style={s.infoTitle}>What happens when you upload?</p>
          <div style={s.infoGrid}>
            {[
              { n: '1', icon: '🔍', title: 'Page Scan', desc: 'AI reads every page and locates financial tables' },
              { n: '2', icon: '🤖', title: 'AI Extraction', desc: 'Values extracted with confidence scores and page references' },
              { n: '3', icon: '🗺️', title: 'Auto Mapping', desc: 'Fields mapped to KSERC regulatory cost heads automatically' },
              { n: '4', icon: '✍️', title: 'Human Review', desc: 'You verify & confirm AI suggestions in the Mapping Workbench' },
            ].map((step) => (
              <div key={step.n} style={s.infoStep}>
                <div style={s.infoIconWrap}>{step.icon}</div>
                <div>
                  <p style={s.infoStepTitle}>{step.title}</p>
                  <p style={s.infoStepDesc}>{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  pageHeader: { marginBottom: '1.5rem' },
  pageTitle: { fontSize: '1.4rem', fontWeight: 800, color: '#1a202c', margin: '0 0 0.35rem' },
  pageDesc: { fontSize: '0.88rem', color: '#718096', margin: 0, lineHeight: 1.6 },

  // Drop Zone
  dropzone: {
    border: '2px dashed #cbd5e0', borderRadius: '20px', padding: '3.5rem 2rem',
    textAlign: 'center' as const, cursor: 'pointer', transition: 'all 0.25s ease',
    background: '#fff', marginBottom: '1.5rem',
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
  },
  dropzoneActive: {
    borderColor: '#3182ce', background: 'rgba(49,130,206,0.04)',
    boxShadow: '0 0 0 4px rgba(49,130,206,0.1)',
  },
  dropLabel: { cursor: 'pointer', display: 'block' },
  dropIconWrap: {
    width: '72px', height: '72px', borderRadius: '50%',
    background: 'rgba(49,130,206,0.06)', border: '1.5px solid rgba(49,130,206,0.15)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    margin: '0 auto 1rem', transition: 'all 0.25s ease',
  },
  dropIconWrapActive: {
    background: 'rgba(49,130,206,0.12)', borderColor: '#3182ce',
    transform: 'scale(1.08)',
  },
  dropMain: { fontSize: '0.95rem', color: '#4a5568', margin: '0 0 0.4rem' },
  browse: { color: '#3182ce', fontWeight: 700, textDecoration: 'underline', cursor: 'pointer' },
  dropHint: { fontSize: '0.78rem', color: '#a0aec0', margin: 0 },

  // Progress Card
  progressCard: {
    background: '#fff', borderRadius: '20px', padding: '2rem',
    boxShadow: '0 4px 24px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0',
    marginBottom: '1.5rem',
  },
  progressHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.75rem' },
  progressTitle: { fontSize: '1.05rem', fontWeight: 700, color: '#1a202c', margin: 0 },
  progressSub: { fontSize: '0.78rem', color: '#a0aec0', margin: '0.2rem 0 0', fontFamily: "'JetBrains Mono', monospace" },
  spinnerLg: {
    width: '36px', height: '36px', borderRadius: '50%',
    border: '3px solid #ebf8ff', borderTopColor: '#3182ce',
    animation: 'spin 0.8s linear infinite', flexShrink: 0,
  },

  // Timeline
  timeline: { display: 'flex', flexDirection: 'column' as const, gap: 0, marginBottom: '1.25rem' },
  timelineRow: { display: 'flex', alignItems: 'center', gap: '0.85rem', paddingBottom: '0.1rem', position: 'relative' as const },
  connector: { position: 'absolute' as const, left: '13px', top: '-50%', width: '2px', height: '50%', transition: 'background 0.4s ease' },
  stepNode: {
    width: '28px', height: '28px', borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, transition: 'all 0.3s ease', zIndex: 1,
  },
  stepNodeDone: { background: '#276749', border: '2px solid #276749', color: '#fff' },
  stepNodeActive: { background: '#ebf8ff', border: '2px solid #3182ce', color: '#3182ce', boxShadow: '0 0 0 4px rgba(49,130,206,0.15)' },
  stepNodePending: { background: '#f7fafc', border: '2px solid #e2e8f0', color: '#a0aec0' },
  stepSpinner: {
    display: 'inline-block', width: '12px', height: '12px',
    border: '2px solid #bee3f8', borderTopColor: '#3182ce',
    borderRadius: '50%', animation: 'spin 0.7s linear infinite',
  },
  stepLabel: {
    fontSize: '0.85rem', fontWeight: 500, padding: '0.6rem 0',
    display: 'flex', alignItems: 'center', gap: '0.3rem', transition: 'color 0.3s',
  },
  stepLabelActive: { color: '#2c5282', fontWeight: 700 },
  stepLabelDone: { color: '#276749' },
  stepLabelPending: { color: '#a0aec0' },
  stepBlink: { animation: 'blink 1.2s ease infinite', marginLeft: '0.15rem', color: '#3182ce' },

  progressNote: {
    fontSize: '0.78rem', color: '#718096', fontStyle: 'italic',
    background: '#f7fafc', borderRadius: '8px', padding: '0.6rem 0.9rem',
    borderLeft: '3px solid #bee3f8',
  },

  // Results Card
  resultsCard: {
    background: '#fff', borderRadius: '20px', padding: '1.75rem',
    boxShadow: '0 4px 24px rgba(0,0,0,0.07)', border: '1.5px solid #9ae6b4',
    marginBottom: '1.5rem',
  },
  resultsHeaderRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
    marginBottom: '1.25rem',
  },
  resultsTitle: { fontSize: '1.1rem', fontWeight: 800, color: '#22543d', margin: 0 },
  resultsFile: { fontSize: '0.8rem', color: '#718096', margin: '0.2rem 0 0', fontFamily: "'JetBrains Mono', monospace" },
  uploadAgainBtn: {
    fontSize: '0.78rem', background: '#f7fafc', color: '#4a5568',
    border: '1.5px solid #e2e8f0', padding: '0.4rem 0.9rem',
    borderRadius: '8px', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600,
  },
  statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' },
  statBox: {
    background: 'var(--surface-1, #f8fafc)', borderRadius: '12px', padding: '1rem',
    textAlign: 'center' as const, border: '1px solid #e2e8f0',
    display: 'flex', flexDirection: 'column' as const, gap: '0.2rem',
  },
  statVal: { fontSize: '2rem', fontWeight: 800, lineHeight: 1 },
  statLbl: { fontSize: '0.7rem', color: '#a0aec0', textTransform: 'uppercase' as const, letterSpacing: '0.05em', fontWeight: 600 },

  // Table
  tableWrap: { marginBottom: '1.5rem' },
  tableTitle: { fontSize: '0.85rem', fontWeight: 700, color: '#2d3748', margin: '0 0 0.6rem' },
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '0.82rem' },
  th: {
    textAlign: 'left' as const, padding: '0.5rem 0.7rem',
    background: '#f7fafc', borderBottom: '2px solid #e2e8f0',
    color: '#4a5568', fontWeight: 700, fontSize: '0.72rem',
    textTransform: 'uppercase' as const, letterSpacing: '0.04em',
  },
  td: { padding: '0.45rem 0.7rem', borderBottom: '1px solid #f0f4f8', color: '#4a5568', verticalAlign: 'middle' as const },
  sbuPill: {
    fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.45rem',
    borderRadius: '4px', letterSpacing: '0.03em',
  },
  confBar: {
    display: 'flex', alignItems: 'center', gap: '0.5rem',
    background: '#f0f4f8', borderRadius: '999px', padding: '0.2rem 0.5rem 0.2rem 0',
    overflow: 'hidden', position: 'relative' as const, height: '22px',
  },
  confFill: {
    position: 'absolute' as const, left: 0, top: 0, bottom: 0,
    borderRadius: '999px', opacity: 0.15, transition: 'width 0.5s ease',
  },
  confLabel: { fontSize: '0.72rem', fontWeight: 700, position: 'relative' as const, paddingLeft: '0.5rem' },
  moreNote: { fontSize: '0.75rem', color: '#a0aec0', fontStyle: 'italic', textAlign: 'center' as const, margin: '0.5rem 0 0' },

  workbenchBtn: {
    display: 'inline-block',
    background: 'linear-gradient(135deg, #276749 0%, #38a169 100%)',
    color: '#fff', padding: '0.7rem 1.5rem', borderRadius: '12px',
    textDecoration: 'none', fontWeight: 700, fontSize: '0.9rem',
    boxShadow: '0 4px 14px rgba(56,161,105,0.3)',
    transition: 'all 0.2s ease',
  },

  // Info Card
  infoCard: {
    background: '#fff', borderRadius: '16px', padding: '1.5rem',
    boxShadow: '0 1px 6px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0',
  },
  infoTitle: { fontSize: '0.88rem', fontWeight: 700, color: '#2d3748', margin: '0 0 1rem' },
  infoGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' },
  infoStep: { display: 'flex', gap: '0.75rem', alignItems: 'flex-start' },
  infoIconWrap: {
    width: '36px', height: '36px', borderRadius: '10px', background: '#ebf8ff',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: '1.1rem', flexShrink: 0,
  },
  infoStepTitle: { fontSize: '0.83rem', fontWeight: 700, color: '#2d3748', margin: '0 0 0.2rem' },
  infoStepDesc: { fontSize: '0.78rem', color: '#718096', margin: 0, lineHeight: 1.5 },
};
