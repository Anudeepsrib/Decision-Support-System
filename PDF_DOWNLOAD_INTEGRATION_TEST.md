# KSERC DSS PDF Download Integration Test

## Test Script for PDF Download Functionality

### Prerequisites
1. Backend running on port 8000
2. Frontend running on port 3000
3. Demo mode enabled for testing

### Test Steps

#### 1. Generate a Test PDF
```bash
# Enable Demo Mode (if not already enabled)
echo "DEMO_MODE=true" >> .env
echo "REACT_APP_DEMO_MODE=true" >> frontend/.env

# Restart services
# Backend: Ctrl+C and restart uvicorn
# Frontend: Ctrl+C and restart npm start
```

#### 2. Test PDF Generation
```bash
# Generate a demo PDF
curl -X POST http://localhost:8000/api/v1/cases/demo-case-001/generate-pdf \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "DRAFT"}'
```

Expected Response:
```json
{
  "status": "success",
  "version": "v1",
  "mode": "DRAFT",
  "download_url": "/api/v1/cases/demo-case-001/download-pdf?version=v1"
}
```

#### 3. Test PDF Download - Version Specific
```bash
# Download the generated PDF
curl -X GET http://localhost:8000/api/v1/cases/demo-case-001/download-pdf?version=v1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output test_download_v1.pdf
```

#### 4. Test PDF Download - Latest
```bash
# Download the latest PDF
curl -X GET http://localhost:8000/api/v1/cases/demo-case-001/latest-pdf \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output test_download_latest.pdf
```

#### 5. Test Document History
```bash
# Get document history
curl -X GET http://localhost:8000/api/v1/cases/demo-case-001/documents \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected Response:
```json
{
  "case_id": "demo-case-001",
  "order_id": "ORDER-SBU-D-2024-25",
  "total_documents": 1,
  "documents": [
    {
      "document_id": "...",
      "version": "v1",
      "mode": "DRAFT",
      "file_hash": "...",
      "file_size": 12345,
      "generated_at": "2026-04-06T...",
      "generated_by": "Demo Admin",
      "download_count": 0,
      "is_finalized": false
    }
  ]
}
```

### Frontend Integration Test

#### 1. Access PDF Generation Center
1. Navigate to http://localhost:3000
2. Go to Manual Decisions tab
3. Scroll to PDF Generation Center
4. Verify demo case ID is pre-filled: `demo-case-001`

#### 2. Test PDF Generation
1. Click "Generate Demo PDF" button
2. Verify success toast appears
3. Verify document history updates

#### 3. Test PDF Download
1. Click "Download Latest" button
2. Verify PDF downloads with filename: `KSERC_Order_Latest_demo-case-001.pdf`
3. Check that PDF contains demo watermark

#### 4. Test Version Download
1. In document history table, click "Download" button
2. Verify PDF downloads with filename: `KSERC_Order_v1.pdf`
3. Verify PDF content matches

### Error Handling Tests

#### 1. Test Missing Document
```bash
# Try to download non-existent version
curl -X GET http://localhost:8000/api/v1/cases/demo-case-001/download-pdf?version=v999 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected Response: `404 Not Found` with detail "Document not found"

#### 2. Test Missing Case
```bash
# Try to download from non-existent case
curl -X GET http://localhost:8000/api/v1/cases/non-existent-case/download-pdf \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected Response: `404 Not Found`

#### 3. Test Unauthorized Access
```bash
# Try without authorization
curl -X GET http://localhost:8000/api/v1/cases/demo-case-001/download-pdf?version=v1
```

Expected Response: `401 Unauthorized`

### File Structure Verification

After successful PDF generation, verify the file structure:
```
generated_docs/
└── demo-case-001/
    └── ORDER-SBU-D-2024-25_v1_DRAFT.pdf
```

### Demo Mode Verification

1. Verify PDF contains demo watermark: "DEMO MODE — NOT FOR REGULATORY USE"
2. Verify download filename includes mode: `..._DRAFT.pdf`
3. Verify audit log shows `[DEMO MODE]` flag

### Production Mode Test

1. Set `DEMO_MODE=false` in `.env`
2. Restart services
3. Verify demo data is not available
4. Verify authentication is required
5. Test with real case data (if available)

### Integration Checklist

- [ ] Backend starts without errors
- [ ] Frontend loads without errors
- [ ] PDF generation works in demo mode
- [ ] PDF download works for specific versions
- [ ] PDF download works for latest version
- [ ] Document history displays correctly
- [ ] Error handling works for missing files
- [ ] Authentication is enforced
- [ ] File paths are created correctly
- [ ] Demo watermarks appear on PDFs
- [ ] Download tracking updates in database
- [ ] Audit logs are created

### Troubleshooting

#### Common Issues

1. **"PDF file not found on disk"**
   - Check if `generated_docs/` directory exists
   - Verify PDF generation completed successfully
   - Check file permissions

2. **"Cannot access PDF file"**
   - Verify file is not corrupted
   - Check file permissions
   - Ensure file is not locked by another process

3. **"Document not found"**
   - Verify case ID is correct
   - Check if PDF was generated for that case
   - Use document history endpoint to verify

4. **"401 Unauthorized"**
   - Verify token is valid
   - Check if user has required permissions
   - In demo mode, authentication should be bypassed

5. **Frontend download fails**
   - Check browser console for errors
   - Verify network requests are successful
   - Check if popup blockers are interfering

### Performance Considerations

- Large PDFs (>10MB) may take longer to download
- Consider implementing progress indicators for large files
- Monitor disk space in `generated_docs/` directory
- Consider implementing cleanup for old PDF versions

### Security Notes

- PDF files are stored in `generated_docs/` directory
- Access is controlled by JWT authentication
- Download actions are logged in audit trail
- Demo mode PDFs are clearly marked as non-regulatory
- File paths use UUIDs to prevent enumeration attacks
