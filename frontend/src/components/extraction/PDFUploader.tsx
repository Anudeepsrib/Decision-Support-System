import React, { useCallback, useState } from 'react';
import { toast } from 'react-toastify';
import { ExtractionService } from '../../services/api';
import { ExtractionResponse } from '../../services/types';

interface PDFUploaderProps {
  onUploadComplete: (response: ExtractionResponse) => void;
}

export function PDFUploader({ onUploadComplete }: PDFUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

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
    try {
      const response = await ExtractionService.uploadPDF(file);
      toast.success(`Extracted ${response.total_fields_extracted} fields from ${response.total_pages_processed} pages`);
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
        }}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileInput}
          style={{ display: 'none' }}
          id="file-upload"
        />
        <label htmlFor="file-upload" style={styles.dropLabel}>
          <div style={styles.uploadIcon}>
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect width="48" height="48" rx="12" fill={dragActive ? '#ebf8ff' : '#f7fafc'} />
              <path d="M24 16v16M16 24l8-8 8 8" stroke={dragActive ? '#3182ce' : '#a0aec0'} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          {dragActive ? (
            <p style={{ ...styles.dropText, color: '#3182ce' }}>Drop the PDF here...</p>
          ) : (
            <>
              <p style={styles.dropText}>Drag & drop a PDF file here, or <span style={styles.browseLink}>click to browse</span></p>
              <p style={styles.dropHint}>Supports: PDF files up to 50MB</p>
            </>
          )}
          {uploading && (
            <div style={styles.loadingSection}>
              <div style={styles.spinnerContainer}>
                <div style={styles.spinner} />
              </div>
              <p style={styles.loadingText}>Extracting data with AI...</p>
            </div>
          )}
        </label>
      </div>

      <div style={styles.infoCard}>
        <h3 style={styles.infoTitle}>What happens next?</h3>
        <div style={styles.stepsList}>
          <div style={styles.step}><span style={styles.stepNum}>1</span> AI scans all pages and detects tables</div>
          <div style={styles.step}><span style={styles.stepNum}>2</span> Financial figures are extracted with confidence scores</div>
          <div style={styles.step}><span style={styles.stepNum}>3</span> Results are sent to the Mapping Workbench for review</div>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  pageTitle: {
    fontSize: '1.35rem',
    fontWeight: 600,
    color: '#1a365d',
    margin: '0 0 0.5rem',
  },
  pageDesc: {
    fontSize: '0.9rem',
    color: '#718096',
    margin: '0 0 1.5rem',
  },
  dropzone: {
    border: '2px dashed #cbd5e0',
    borderRadius: '16px',
    padding: '3rem 2rem',
    textAlign: 'center' as const,
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    background: '#fafbfc',
    marginBottom: '1.5rem',
  },
  dropzoneActive: {
    borderColor: '#3182ce',
    background: '#ebf8ff',
  },
  dropLabel: {
    cursor: 'pointer',
    display: 'block',
  },
  uploadIcon: {
    marginBottom: '1rem',
  },
  dropText: {
    fontSize: '0.95rem',
    color: '#4a5568',
    margin: '0 0 0.5rem',
  },
  browseLink: {
    color: '#3182ce',
    fontWeight: 600,
    textDecoration: 'underline',
  },
  dropHint: {
    fontSize: '0.8rem',
    color: '#a0aec0',
    margin: 0,
  },
  loadingSection: {
    marginTop: '1.5rem',
  },
  spinnerContainer: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '0.5rem',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid #e2e8f0',
    borderTopColor: '#3182ce',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    fontSize: '0.85rem',
    color: '#718096',
    margin: 0,
  },
  infoCard: {
    background: '#fff',
    borderRadius: '12px',
    padding: '1.25rem',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    border: '1px solid #edf2f7',
  },
  infoTitle: {
    fontSize: '0.95rem',
    fontWeight: 600,
    color: '#2d3748',
    margin: '0 0 0.75rem',
  },
  stepsList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '0.6rem',
  },
  step: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    fontSize: '0.85rem',
    color: '#4a5568',
  },
  stepNum: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    background: '#ebf8ff',
    color: '#3182ce',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.75rem',
    fontWeight: 700,
    flexShrink: 0,
  },
};
