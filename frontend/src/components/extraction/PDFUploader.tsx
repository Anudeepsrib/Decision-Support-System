import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';
import { ExtractionService } from '../../services/api';
import { ExtractionResponse } from '../../services/types';

interface PDFUploaderProps {
  onUploadComplete: (response: ExtractionResponse) => void;
}

export function PDFUploader({ onUploadComplete }: PDFUploaderProps) {
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      toast.error('Please upload a PDF file');
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      toast.error('File size must be less than 50MB');
      return;
    }

    const loadingToast = toast.loading('Uploading and processing PDF...');

    try {
      const response = await ExtractionService.uploadPDF(file);
      toast.dismiss(loadingToast);
      toast.success(`Extracted ${response.total_fields_extracted} fields from ${response.total_pages_processed} pages`);
      onUploadComplete(response);
    } catch (error) {
      toast.dismiss(loadingToast);
      toast.error(error instanceof Error ? error.message : 'Upload failed');
    }
  }, [onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      }`}
    >
      <input {...getInputProps()} />
      <div className="text-4xl mb-4">📄</div>
      {isDragActive ? (
        <p className="text-blue-600">Drop the PDF here...</p>
      ) : (
        <>
          <p className="text-gray-600 mb-2">Drag & drop a PDF file here, or click to select</p>
          <p className="text-sm text-gray-400">Max file size: 50MB</p>
        </>
      )}
    </div>
  );
}
