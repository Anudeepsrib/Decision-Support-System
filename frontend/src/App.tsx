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

interface ExtractionResult {
  document_id: string
  total_rows_extracted: number
  rows_needing_review: number
  rows: Array<{
    id: string
    row_label: string
    value: number
    confidence: number
  }>
}

interface ComparisonItem {
  id: string
  canonical_name: string
  approved_value: number
  actual_value: number
  variance: number
  variance_percent: number
  decision_class: string
}

interface ComparisonResult {
  case_id: string
  financial_year: string
  total_items: number
  auto_approved: number
  review_required: number
  total_variance: number
  items: ComparisonItem[]
}

interface OrderResult {
  id: string
  download_url: string
}

function App() {
  const [activeTab, setActiveTab] = useState('upload')
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [extracting, setExtracting] = useState<string | null>(null)
  
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null)
  const [comparison, setComparison] = useState<ComparisonResult | null>(null)
  const [order, setOrder] = useState<OrderResult | null>(null)

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
    
    // Auto-detect document type from filename
    const isPetition = selectedFile.name.toLowerCase().includes('petition')
    formData.append('doc_type', isPetition ? 'truing_up_petition' : 'arr_order')
    formData.append('financial_year', '2024-25')

    try {
      const response = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        setSelectedFile(null)
        loadDocuments()
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

  const runExtraction = async (docId: string) => {
    setExtracting(docId)
    try {
      const response = await fetch(`http://localhost:8000/api/extraction/${docId}/run`, { method: 'POST' })
      if (response.ok) {
        const res = await response.json()
        setExtraction(res)
        loadDocuments()
        setActiveTab('extraction')
      }
    } catch (error) {
      console.error(error)
    } finally {
      setExtracting(null)
    }
  }

  const runComparison = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/comparison/run?financial_year=2024-25', { method: 'POST' })
      if (response.ok) {
        const res = await response.json()
        setComparison(res)
        setActiveTab('comparison')
      }
    } catch (error) {
      console.error(error)
    }
  }

  const approveItem = async (compId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/review/${compId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'approve', officer_name: 'Demo Officer', officer_comment: 'Approved manually.' })
      })
      if (response.ok) {
        if (comparison) {
          const updatedItems = comparison.items.map(i => i.id === compId ? { ...i, decision_class: 'AI_AUTO' } : i)
          setComparison({ ...comparison, items: updatedItems, auto_approved: comparison.auto_approved + 1, review_required: Math.max(0, comparison.review_required - 1) })
        }
      }
    } catch (error) {
      console.error(error)
    }
  }

  const generateOrder = async () => {
    if (!comparison) return
    try {
      const response = await fetch('http://localhost:8000/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: comparison.case_id, financial_year: '2024-25', officer_name: 'Demo Officer' })
      })
      if (response.ok) {
        const res = await response.json()
        setOrder(res)
      }
    } catch (error) {
      console.error(error)
    }
  }

  const renderUploadTab = () => (
    <div className="max-w-4xl mx-auto p-6">
      <div className="kserc-card bg-white p-6 shadow-md rounded-lg">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Upload Documents</h2>
        
        <div className="border-2 border-dashed border-blue-300 rounded-lg p-8 text-center bg-blue-50">
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <span className="bg-blue-600 text-white font-medium py-2 px-4 rounded shadow hover:bg-blue-700 transition">
              Choose PDF File
            </span>
          </label>
          
          {selectedFile && (
            <div className="mt-4">
              <p className="text-sm text-gray-600">Selected: <span className="font-semibold">{selectedFile.name}</span></p>
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="mt-4 bg-green-600 text-white font-medium py-2 px-6 rounded shadow hover:bg-green-700 disabled:bg-gray-400 transition"
              >
                {uploading ? 'Uploading...' : 'Upload Document'}
              </button>
            </div>
          )}
        </div>

        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4 border-b pb-2">Recent Uploads</h3>
          {documents.length === 0 ? (
            <p className="text-gray-500 italic text-sm">No documents uploaded yet.</p>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div key={doc.id} className="border border-gray-200 rounded-lg p-4 flex justify-between items-center bg-gray-50">
                  <div>
                    <p className="font-bold text-gray-800">{doc.filename}</p>
                    <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Type: {doc.doc_type}</p>
                    <p className="text-sm text-gray-500">
                      {doc.page_count} pages • {(doc.file_size / 1024 / 1024).toFixed(2)} MB • Status: <span className="font-semibold text-blue-600">{doc.status}</span>
                    </p>
                  </div>
                  <button 
                    onClick={() => runExtraction(doc.id)}
                    disabled={extracting === doc.id}
                    className="bg-indigo-100 text-indigo-700 hover:bg-indigo-200 py-1 px-4 rounded font-medium text-sm transition"
                  >
                    {extracting === doc.id ? 'Extracting...' : 'Extract Data'}
                  </button>
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
      <div className="kserc-card bg-white p-6 shadow-md rounded-lg">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Table Extraction Results</h2>
        {!extraction ? (
          <p className="text-gray-500">Run extraction from the Upload tab to view extracted financial tables.</p>
        ) : (
          <div>
            <div className="flex gap-4 mb-6">
              <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg flex-1">
                <p className="text-blue-800 font-semibold">Total Rows Extracted</p>
                <p className="text-2xl font-bold">{extraction.total_rows_extracted}</p>
              </div>
              <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg flex-1">
                <p className="text-yellow-800 font-semibold">Rows Needing Review (Low Confidence)</p>
                <p className="text-2xl font-bold">{extraction.rows_needing_review}</p>
              </div>
            </div>
            <div className="overflow-auto max-h-96 border rounded">
              <table className="min-w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-gray-100 sticky top-0">
                  <tr>
                    <th className="p-3 font-semibold text-gray-700">Line Item Label</th>
                    <th className="p-3 font-semibold text-gray-700">Extracted Value</th>
                    <th className="p-3 font-semibold text-gray-700">Confidence Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {extraction.rows.slice(0, 100).map(r => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="p-3">{r.row_label}</td>
                      <td className="p-3 font-mono">{r.value}</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${r.confidence > 0.8 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {(r.confidence * 100).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )

  const renderComparisonTab = () => (
    <div className="max-w-6xl mx-auto p-6">
      <div className="kserc-card bg-white p-6 shadow-md rounded-lg">
        <div className="flex justify-between items-center mb-6 border-b pb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Variance Comparison & Review</h2>
            <p className="text-sm text-gray-500 mt-1">Cross-reference ARR Order (Approved) against Truing-up Petition (Actual)</p>
          </div>
          <button onClick={runComparison} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium shadow transition">
            Run AI Comparison
          </button>
        </div>
        
        {!comparison ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Click "Run AI Comparison" to generate variance analysis between uploaded documents.</p>
          </div>
        ) : (
          <div>
            <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-50 border border-gray-200 p-4 rounded-lg">
                <p className="text-gray-600 font-semibold text-sm">Total Line Items</p>
                <p className="text-2xl font-bold">{comparison.total_items}</p>
              </div>
              <div className="bg-green-50 border border-green-200 p-4 rounded-lg">
                <p className="text-green-800 font-semibold text-sm">AI Auto-Approved (&lt;15% variance)</p>
                <p className="text-2xl font-bold text-green-700">{comparison.auto_approved}</p>
              </div>
              <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
                <p className="text-red-800 font-semibold text-sm">Review Required (≥15% variance)</p>
                <p className="text-2xl font-bold text-red-700">{comparison.review_required}</p>
              </div>
            </div>
            
            <div className="overflow-auto border rounded-lg shadow-sm">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="p-3 font-semibold text-gray-700">Line Item</th>
                    <th className="p-3 font-semibold text-gray-700 text-right">Approved (Rs. Cr)</th>
                    <th className="p-3 font-semibold text-gray-700 text-right">Actual (Rs. Cr)</th>
                    <th className="p-3 font-semibold text-gray-700 text-right">Variance</th>
                    <th className="p-3 font-semibold text-gray-700 text-center">AI Classification</th>
                    <th className="p-3 font-semibold text-gray-700 text-center">Officer Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {comparison.items.map(i => (
                    <tr key={i.id} className="hover:bg-gray-50">
                      <td className="p-3 font-medium">{i.canonical_name}</td>
                      <td className="p-3 text-right font-mono">{i.approved_value?.toFixed(2) || '—'}</td>
                      <td className="p-3 text-right font-mono">{i.actual_value?.toFixed(2) || '—'}</td>
                      <td className={`p-3 text-right font-mono ${Math.abs(i.variance_percent) >= 15 ? 'text-red-600 font-bold' : 'text-green-600'}`}>
                        {i.variance_percent > 0 ? '+' : ''}{i.variance_percent?.toFixed(2) || 0}%
                      </td>
                      <td className="p-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                          i.decision_class === 'AI_AUTO' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {i.decision_class === 'AI_AUTO' ? 'Auto-Approved' : 'Review Required'}
                        </span>
                      </td>
                      <td className="p-3 text-center">
                        {i.decision_class !== 'AI_AUTO' ? (
                          <button 
                            onClick={() => approveItem(i.id)} 
                            className="text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 font-medium px-3 py-1 rounded transition"
                          >
                            Approve Override
                          </button>
                        ) : (
                          <span className="text-gray-400 text-xs">Reviewed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )

  const renderGenerateTab = () => (
    <div className="max-w-6xl mx-auto p-6">
      <div className="kserc-card bg-white p-8 shadow-md rounded-lg text-center">
        <h2 className="text-3xl font-bold mb-4 text-gray-900">Generate Official Order</h2>
        <p className="mb-8 text-gray-600 max-w-2xl mx-auto">
          Generate a high-quality, formatted KSERC Truing-up Order PDF using Playwright's Headless Chromium renderer. The generated PDF includes AI-assisted variance calculations and automated narratives.
        </p>
        
        <button 
          onClick={generateOrder} 
          disabled={!comparison} 
          className={`px-8 py-3 rounded-lg font-bold text-white shadow-lg transition-all ${
            comparison ? 'bg-blue-600 hover:bg-blue-700 transform hover:-translate-y-1' : 'bg-gray-400 cursor-not-allowed'
          }`}
        >
          {comparison ? 'Generate PDF Draft Order' : 'Run Comparison First'}
        </button>
        
        {order && (
          <div className="mt-8 p-6 bg-green-50 border-2 border-green-200 rounded-lg max-w-md mx-auto">
            <div className="flex items-center justify-center text-green-600 mb-2">
              <svg className="w-8 h-8 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <h3 className="text-xl font-bold text-green-800">Order Generated Successfully!</h3>
            </div>
            <a 
              href={`http://localhost:8000${order.download_url}`} 
              target="_blank" 
              rel="noreferrer" 
              className="mt-4 inline-block bg-white text-green-700 font-bold border border-green-300 hover:bg-green-100 py-2 px-6 rounded shadow transition"
            >
              Download PDF Output
            </a>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-blue-900 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold tracking-tight">KSERC Decision Support System</h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium text-blue-200">Playwright PDF Engine</span>
              <span className="px-3 py-1 bg-green-500 text-white text-xs font-bold rounded-full shadow">
                INTEGRATED MVP
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white shadow-sm sticky top-0 z-10 border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-1">
            {[
              { id: 'upload', label: '1. Upload', icon: '📄' },
              { id: 'extraction', label: '2. Data Extraction', icon: '📊' },
              { id: 'comparison', label: '3. AI Comparison & Review', icon: '📈' },
              { id: 'generate', label: '4. Generate KSERC Order', icon: '📋' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-6 font-semibold text-sm transition-colors border-b-4 ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-700 bg-blue-50'
                    : 'border-transparent text-gray-500 hover:text-gray-800 hover:bg-gray-50 hover:border-gray-300'
                }`}
              >
                <span className="mr-2 text-lg">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="py-8">
        {activeTab === 'upload' && renderUploadTab()}
        {activeTab === 'extraction' && renderExtractionTab()}
        {activeTab === 'comparison' && renderComparisonTab()}
        {activeTab === 'generate' && renderGenerateTab()}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto shadow-inner">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm font-medium text-gray-500">
            KSERC Decision Support System MVP • Fully Integrated API
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
