import { useState, useEffect } from 'react'
import './index.css'

interface Document {
  id: string
  filename: string
  upload_timestamp: string
  file_size: number
  page_count: number
  status: string
  doc_type: string
  financial_year: string
}

function App() {
  const [activeTab, setActiveTab] = useState('upload')
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  // Load documents on component mount
  useEffect(() => {
    loadDocuments()
  }, [])

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('doc_type', 'arr_order')
    formData.append('financial_year', '2024-25')

    try {
      const response = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const result = await response.json()
        console.log('Upload successful:', result)
        setSelectedFile(null)
        // Refresh documents list
        loadDocuments()
      } else {
        const error = await response.text()
        console.error('Upload failed:', error)
      }
    } catch (error) {
      console.error('Upload error:', error)
    } finally {
      setUploading(false)
    }
  }

  const loadDocuments = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/documents')
      if (response.ok) {
        const docs = await response.json()
        setDocuments(docs)
      }
    } catch (error) {
      console.error('Failed to load documents:', error)
    }
  }

  const renderUploadTab = () => (
    <div className="max-w-4xl mx-auto p-6">
      <div className="kserc-card">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Upload Documents</h2>
        
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <span className="kserc-button">
              Choose PDF File
            </span>
          </label>
          
          {selectedFile && (
            <div className="mt-4">
              <p className="text-sm text-gray-600">Selected: {selectedFile.name}</p>
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="mt-2 kserc-button"
              >
                {uploading ? 'Uploading...' : 'Upload Document'}
              </button>
            </div>
          )}
        </div>

        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4">Recent Uploads</h3>
          {documents.length === 0 ? (
            <div className="text-center py-8">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-gray-500 font-medium">No documents uploaded yet</p>
              <p className="text-gray-400 text-sm mt-2">Upload PDF documents to begin extraction</p>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <div key={doc.id} className="border border-gray-200 rounded p-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium">{doc.filename}</p>
                      <p className="text-sm text-gray-500">
                        {doc.page_count} pages • {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      doc.status === 'extracted' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {doc.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )

  const renderExtractionTab = () => (
    <div className="max-w-6xl mx-auto p-6">
      <div className="kserc-card">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Table Extraction</h2>
        <p className="text-gray-600">Extracted financial tables will appear here with confidence scores.</p>
        
        <div className="mt-6 p-8 border-2 border-dashed border-gray-300 rounded-lg text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v1a1 1 0 001 1h4a1 1 0 001-1v-1m3-2V8a2 2 0 00-2-2H8a2 2 0 00-2 2v6m3-2h6" />
          </svg>
          <p className="text-gray-500">Upload a document to see extracted tables</p>
        </div>
      </div>
    </div>
  )

  const renderComparisonTab = () => (
    <div className="max-w-6xl mx-auto p-6">
      <div className="kserc-card">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Variance Comparison</h2>
        <p className="text-gray-600">Compare approved vs actual values with variance analysis.</p>
        
        <div className="mt-6 p-8 border-2 border-dashed border-gray-300 rounded-lg text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-gray-500">Run comparison to see variance analysis</p>
        </div>
      </div>
    </div>
  )

  const renderReviewTab = () => (
    <div className="max-w-6xl mx-auto p-6">
      <div className="kserc-card">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Officer Review</h2>
        <p className="text-gray-600">Review flagged items with variance ≥ 15%.</p>
        
        <div className="mt-6 p-8 border-2 border-dashed border-gray-300 rounded-lg text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-500">No items requiring review at this time</p>
        </div>
      </div>
    </div>
  )

  const renderGenerateTab = () => (
    <div className="max-w-6xl mx-auto p-6">
      <div className="kserc-card">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Generate Order</h2>
        <p className="text-gray-600">Generate KSERC-style truing-up draft order.</p>
        
        <div className="mt-6 p-8 border-2 border-dashed border-gray-300 rounded-lg text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-500">Complete review process to generate order</p>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-blue-900">KSERC Decision Support System</h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">MVP Demo</span>
              <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                Operational
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            {[
              { id: 'upload', label: 'Upload', icon: '📄' },
              { id: 'extraction', label: 'Extraction', icon: '📊' },
              { id: 'comparison', label: 'Comparison', icon: '📈' },
              { id: 'review', label: 'Review', icon: '✅' },
              { id: 'generate', label: 'Generate', icon: '📋' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="py-6">
        {activeTab === 'upload' && renderUploadTab()}
        {activeTab === 'extraction' && renderExtractionTab()}
        {activeTab === 'comparison' && renderComparisonTab()}
        {activeTab === 'review' && renderReviewTab()}
        {activeTab === 'generate' && renderGenerateTab()}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500">
            KSERC Decision Support System MVP • Version 1.0.0
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
