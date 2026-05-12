import React, { useState, useEffect } from 'react'

interface Document {
  id: string
  filename: string
  doc_type: string
  financial_year: string
  upload_timestamp: string
  file_size: number
  page_count: number
  status: string
}

interface ExtractedRow {
  id: string
  page_number: number
  table_index: number
  table_name: string
  row_label: string
  value: number
  unit: string
  confidence: number
  extraction_method: string
  raw_text: string
}

interface ExtractionResult {
  document_id: string
  filename: string
  doc_type: string
  total_pages: number
  total_rows_extracted: number
  rows_needing_review: number
  extraction_method: string
  rows: ExtractedRow[]
}

interface ComparisonItem {
  id: string
  canonical_name: string
  cost_head: string
  approved_value: number | null
  actual_value: number | null
  claimed_value: number | null
  variance: number | null
  variance_percent: number | null
  decision_class: string
  flag_reason: string | null
  approved_source_page: number | null
  actual_source_page: number | null
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

interface GeneratedOrder {
  id: string
  case_id: string
  financial_year: string
  file_path: string
  file_size: number
  is_draft: boolean
  total_items: number
  auto_approved: number
  review_required: number
  generated_at: string
  download_url: string
}

function App() {
  const [activeTab, setActiveTab] = useState('arr-upload')
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedArrFile, setSelectedArrFile] = useState<File | null>(null)
  const [selectedPetitionFile, setSelectedPetitionFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [extracting, setExtracting] = useState<string | null>(null)
  
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null)
  const [comparison, setComparison] = useState<ComparisonResult | null>(null)
  const [order, setOrder] = useState<GeneratedOrder | null>(null)

  useEffect(() => {
    loadDocuments()
  }, [])

  const handleArrFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedArrFile(file)
    }
  }

  const handlePetitionFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedPetitionFile(file)
    }
  }

  const handleArrUpload = async () => {
    if (!selectedArrFile) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', selectedArrFile)
    formData.append('financial_year', '2024-25')

    try {
      const response = await fetch('http://127.0.0.1:8000/api/upload/arr', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const result = await response.json()
        console.log('ARR upload successful:', result)
        setSelectedArrFile(null)
        loadDocuments()
        alert(`ARR Order uploaded successfully! ${result.filename}`)
        setActiveTab('petition-upload')
      } else {
        const error = await response.json()
        console.error('ARR upload failed:', error)
        alert(`ARR upload failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('ARR upload error:', error)
      alert(`ARR upload error: ${(error as Error).message}`)
    } finally {
      setUploading(false)
    }
  }

  const handlePetitionUpload = async () => {
    if (!selectedPetitionFile) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', selectedPetitionFile)
    formData.append('financial_year', '2024-25')

    try {
      const response = await fetch('http://127.0.0.1:8000/api/upload/petition', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const result = await response.json()
        console.log('Petition upload successful:', result)
        setSelectedPetitionFile(null)
        loadDocuments()
        alert(`Petition uploaded successfully! ${result.filename}`)
        setActiveTab('extraction')
      } else {
        const error = await response.json()
        console.error('Petition upload failed:', error)
        alert(`Petition upload failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Petition upload error:', error)
      alert(`Petition upload error: ${(error as Error).message}`)
    } finally {
      setUploading(false)
    }
  }

  const loadDocuments = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/documents')
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
      const response = await fetch(`http://127.0.0.1:8000/api/extraction/${docId}/run`, { method: 'POST' })
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
      const response = await fetch('http://127.0.0.1:8000/api/comparison/run?financial_year=2024-25', { method: 'POST' })
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
      const response = await fetch(`http://127.0.0.1:8000/api/review/${compId}`, {
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
      const response = await fetch('http://127.0.0.1:8000/api/generate', {
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

  const renderArrUploadTab = () => (
    <div className="max-w-4xl mx-auto p-6">
      <div className="kserc-card bg-white p-6 shadow-md rounded-lg">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Step 1: Upload ARR Approval Order</h2>
        
        <div className="border-2 border-dashed border-blue-300 rounded-lg p-8 text-center bg-blue-50">
          <input
            type="file"
            accept=".pdf"
            onChange={handleArrFileSelect}
            className="hidden"
            id="arr-file-upload"
          />
          <label htmlFor="arr-file-upload" className="cursor-pointer">
            <span className="bg-blue-600 text-white font-medium py-2 px-4 rounded shadow hover:bg-blue-700 transition">
              Choose ARR Order PDF
            </span>
          </label>
          
          {selectedArrFile && (
            <div className="mt-4">
              <p className="text-sm text-gray-600">Selected: <span className="font-semibold">{selectedArrFile.name}</span></p>
              <button
                onClick={handleArrUpload}
                disabled={uploading}
                className="mt-4 bg-green-600 text-white font-medium py-2 px-6 rounded shadow hover:bg-green-700 disabled:bg-gray-400 transition"
              >
                {uploading ? 'Uploading...' : 'Upload ARR Order'}
              </button>
            </div>
          )}
        </div>

        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4 border-b pb-2">ARR Documents</h3>
          {documents.filter(d => d.doc_type === 'arr_order').length === 0 ? (
            <p className="text-gray-500 italic text-sm">No ARR documents uploaded yet.</p>
          ) : (
            <div className="space-y-3">
              {documents.filter(d => d.doc_type === 'arr_order').map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-3 border rounded-lg bg-gray-50">
                  <div>
                    <p className="font-medium text-gray-900">{doc.filename}</p>
                    <p className="text-sm text-gray-500">
                      {doc.file_size ? `${(doc.file_size / 1024 / 1024).toFixed(1)} MB` : 'Unknown size'} • 
                      {doc.page_count ? `${doc.page_count} pages` : 'Unknown pages'} • 
                      Status: {doc.status}
                    </p>
                  </div>
                  {doc.status === 'uploaded' && (
                    <button
                      onClick={() => runExtraction(doc.id)}
                      disabled={extracting === doc.id}
                      className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400 transition"
                    >
                      {extracting === doc.id ? 'Extracting...' : 'Extract Tables'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )

  const renderPetitionUploadTab = () => (
    <div className="max-w-4xl mx-auto p-6">
      <div className="kserc-card bg-white p-6 shadow-md rounded-lg">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Step 2: Upload Truing-Up Petition</h2>
        
        <div className="border-2 border-dashed border-green-300 rounded-lg p-8 text-center bg-green-50">
          <input
            type="file"
            accept=".pdf"
            onChange={handlePetitionFileSelect}
            className="hidden"
            id="petition-file-upload"
          />
          <label htmlFor="petition-file-upload" className="cursor-pointer">
            <span className="bg-green-600 text-white font-medium py-2 px-4 rounded shadow hover:bg-green-700 transition">
              Choose Petition PDF
            </span>
          </label>
          
          {selectedPetitionFile && (
            <div className="mt-4">
              <p className="text-sm text-gray-600">Selected: <span className="font-semibold">{selectedPetitionFile.name}</span></p>
              <button
                onClick={handlePetitionUpload}
                disabled={uploading}
                className="mt-4 bg-green-600 text-white font-medium py-2 px-6 rounded shadow hover:bg-green-700 disabled:bg-gray-400 transition"
              >
                {uploading ? 'Uploading...' : 'Upload Petition'}
              </button>
            </div>
          )}
        </div>

        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4 border-b pb-2">Petition Documents</h3>
          {documents.filter(d => d.doc_type === 'truing_up_petition').length === 0 ? (
            <p className="text-gray-500 italic text-sm">No petition documents uploaded yet.</p>
          ) : (
            <div className="space-y-3">
              {documents.filter(d => d.doc_type === 'truing_up_petition').map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-3 border rounded-lg bg-gray-50">
                  <div>
                    <p className="font-medium text-gray-900">{doc.filename}</p>
                    <p className="text-sm text-gray-500">
                      {doc.file_size ? `${(doc.file_size / 1024 / 1024).toFixed(1)} MB` : 'Unknown size'} • 
                      {doc.page_count ? `${doc.page_count} pages` : 'Unknown pages'} • 
                      Status: {doc.status}
                    </p>
                  </div>
                  {doc.status === 'uploaded' && (
                    <button
                      onClick={() => runExtraction(doc.id)}
                      disabled={extracting === doc.id}
                      className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400 transition"
                    >
                      {extracting === doc.id ? 'Extracting...' : 'Extract Tables'}
                    </button>
                  )}
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
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Data Extraction Results</h2>
        {!extraction ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">Upload and extract both documents to view extracted financial tables.</p>
            <div className="space-y-2">
              <p className="text-sm text-gray-600">ARR Documents: {documents.filter(d => d.doc_type === 'arr_order' && d.status === 'extracted').length} extracted</p>
              <p className="text-sm text-gray-600">Petition Documents: {documents.filter(d => d.doc_type === 'truing_up_petition' && d.status === 'extracted').length} extracted</p>
              {documents.filter(d => d.doc_type === 'arr_order' && d.status === 'extracted').length > 0 &&
               documents.filter(d => d.doc_type === 'truing_up_petition' && d.status === 'extracted').length > 0 && (
                <button
                  onClick={runComparison}
                  className="mt-4 bg-purple-600 text-white font-medium py-2 px-6 rounded shadow hover:bg-purple-700 transition"
                >
                  Run AI Comparison
                </button>
              )}
            </div>
          </div>
        ) : (
          <div>
            <div className="flex gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="font-semibold text-blue-800">{extraction.filename}</h3>
                <p className="text-sm text-blue-600">Type: {extraction.doc_type}</p>
                <p className="text-sm text-blue-600">Pages: {extraction.total_pages}</p>
                <p className="text-sm text-blue-600">Rows: {extraction.total_rows_extracted}</p>
              </div>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse border border-gray-300">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="border border-gray-300 px-4 py-2 text-left">Line Item</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Value</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">Confidence</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">Page</th>
                  </tr>
                </thead>
                <tbody>
                  {extraction.rows.slice(0, 20).map((row) => (
                    <tr key={row.id} className={row.confidence < 0.6 ? 'bg-yellow-50' : ''}>
                      <td className="border border-gray-300 px-4 py-2">{row.row_label}</td>
                      <td className="border border-gray-300 px-4 py-2 text-right">{row.value?.toFixed(2)}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">
                        <span className={`px-2 py-1 rounded text-xs ${
                          row.confidence >= 0.8 ? 'bg-green-100 text-green-800' :
                          row.confidence >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {(row.confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{row.page_number}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {extraction.rows.length > 20 && (
                <p className="text-sm text-gray-500 mt-2">Showing first 20 rows of {extraction.rows.length} total</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )

  const renderComparisonTab = () => (
    <div className="max-w-7xl mx-auto p-6">
      <div className="kserc-card bg-white p-6 shadow-md rounded-lg">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">AI Comparison & Review</h2>
        
        {!comparison ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">Extract both documents and click "Run AI Comparison" to generate variance analysis.</p>
          </div>
        ) : (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-green-50 p-4 rounded-lg text-center">
                <h3 className="font-semibold text-green-800">Auto-Approved</h3>
                <p className="text-2xl font-bold text-green-600">{comparison.auto_approved}</p>
              </div>
              <div className="bg-yellow-50 p-4 rounded-lg text-center">
                <h3 className="font-semibold text-yellow-800">Review Required</h3>
                <p className="text-2xl font-bold text-yellow-600">{comparison.review_required}</p>
              </div>
              <div className="bg-blue-50 p-4 rounded-lg text-center">
                <h3 className="font-semibold text-blue-800">Total Variance</h3>
                <p className="text-2xl font-bold text-blue-600">Rs. {comparison.total_variance} Cr.</p>
              </div>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse border border-gray-300">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="border border-gray-300 px-4 py-2 text-left">Line Item</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">ARR Approved</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Actual</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Claimed</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Variance</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Variance %</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">Status</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.items.map((item) => (
                    <tr key={item.id} className={
                      item.decision_class === 'AI_AUTO' ? 'bg-green-50' : 'bg-yellow-50'
                    }>
                      <td className="border border-gray-300 px-4 py-2 font-medium">{item.canonical_name}</td>
                      <td className="border border-gray-300 px-4 py-2 text-right">{item.approved_value?.toFixed(2) || '-'}</td>
                      <td className="border border-gray-300 px-4 py-2 text-right">{item.actual_value?.toFixed(2) || '-'}</td>
                      <td className="border border-gray-300 px-4 py-2 text-right">{item.claimed_value?.toFixed(2) || '-'}</td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        {item.variance !== null ? (
                          <span className={item.variance >= 0 ? 'text-red-600' : 'text-green-600'}>
                            {item.variance >= 0 ? '+' : ''}{item.variance.toFixed(2)}
                          </span>
                        ) : '-'}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        {item.variance_percent !== null ? (
                          <span className={item.variance_percent >= 0 ? 'text-red-600' : 'text-green-600'}>
                            {item.variance_percent >= 0 ? '+' : ''}{item.variance_percent.toFixed(1)}%
                          </span>
                        ) : '-'}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-center">
                        <span className={`px-2 py-1 rounded text-xs ${
                          item.decision_class === 'AI_AUTO' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {item.decision_class === 'AI_AUTO' ? 'AUTO' : 'REVIEW'}
                        </span>
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-center">
                        {item.decision_class !== 'AI_AUTO' && (
                          <button
                            onClick={() => approveItem(item.id)}
                            className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition"
                          >
                            Approve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {comparison.review_required === 0 && (
              <div className="mt-6 text-center">
                <button
                  onClick={generateOrder}
                  className="bg-green-600 text-white font-medium py-3 px-8 rounded shadow hover:bg-green-700 transition"
                >
                  Generate KSERC Draft Order
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )

  const renderGenerateTab = () => (
    <div className="max-w-4xl mx-auto p-6">
      <div className="kserc-card bg-white p-6 shadow-md rounded-lg">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Generate KSERC Draft Order</h2>
        
        {!order ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">
              {comparison && comparison.review_required > 0 
                ? `Please review ${comparison.review_required} items before generating the order.`
                : 'Complete the comparison and review process to generate the draft order.'
              }
            </p>
          </div>
        ) : (
          <div className="mt-8 p-6 bg-green-50 border-2 border-green-200 rounded-lg max-w-md mx-auto">
            <div className="flex items-center justify-center text-green-600 mb-2">
              <svg className="w-8 h-8 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <h3 className="text-xl font-bold text-green-800">Order Generated Successfully!</h3>
            </div>
            <a 
              href={`http://127.0.0.1:8000${order.download_url}`} 
              target="_blank" 
              rel="noreferrer" 
              className="mt-4 inline-block bg-white text-green-700 font-bold border border-green-300 hover:bg-green-100 py-2 px-6 rounded shadow transition"
            >
              Download PDF Draft
            </a>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">KSERC Decision Support System</h1>
            <div className="text-sm text-gray-500">
              MVP Demo • Two-Document Workflow
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-1">
            {[
              { id: 'arr-upload', label: '1. ARR Upload', icon: '📄' },
              { id: 'petition-upload', label: '2. Petition Upload', icon: '📋' },
              { id: 'extraction', label: '3. Data Extraction', icon: '📊' },
              { id: 'comparison', label: '4. AI Comparison', icon: '📈' },
              { id: 'generate', label: '5. Generate Order', icon: '📋' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
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
      <main className="py-8">
        {activeTab === 'arr-upload' && renderArrUploadTab()}
        {activeTab === 'petition-upload' && renderPetitionUploadTab()}
        {activeTab === 'extraction' && renderExtractionTab()}
        {activeTab === 'comparison' && renderComparisonTab()}
        {activeTab === 'generate' && renderGenerateTab()}
      </main>
    </div>
  )
}

export default App
