import { useEffect, useMemo, useState } from 'react'
import {
  Check,
  Download,
  Edit3,
  Eye,
  FileText,
  Loader2,
  RefreshCw,
  Upload,
  X,
} from 'lucide-react'

const API_BASE = 'http://127.0.0.1:8000/api'

type Tab = 'arr-upload' | 'petition-upload' | 'extraction' | 'comparison' | 'generate'
type DocType = 'arr_order' | 'truing_up_petition'

interface Document {
  id: string
  filename: string
  doc_type: DocType
  financial_year: string
  upload_timestamp: string
  file_size: number
  page_count: number | null
  status: string
}

interface UploadResponse {
  id: string
  filename: string
  doc_type: DocType
  file_size: number
  page_count: number | null
  status: string
  rows_extracted: number
  case_id?: string | null
}

interface ExtractedRow {
  id: string
  page_number: number
  table_index: number | null
  table_name: string | null
  row_label: string
  normalized_label: string | null
  value: number | null
  value_type: string
  document_type: DocType
  unit: string
  confidence: number
  extraction_method: string
  raw_text: string | null
}

interface ExtractionResult {
  document_id: string
  filename: string
  doc_type: DocType
  total_pages: number
  total_rows_extracted: number
  rows_needing_review: number
  extraction_method: string
  rows: ExtractedRow[]
}

interface ComparisonItem {
  id: string
  canonical_name: string
  cost_head: string | null
  approved_value: number | null
  actual_value: number | null
  claimed_value: number | null
  variance: number | null
  variance_percent: number | null
  decision_class: string
  flag_reason: string | null
  latest_review_action: string | null
  latest_review_comment: string | null
  latest_reviewed_at: string | null
  approved_source_document_id: string | null
  actual_source_document_id: string | null
  claimed_source_document_id: string | null
  approved_source_page: number | null
  actual_source_page: number | null
  claimed_source_page: number | null
  approved_source_table: string | null
  actual_source_table: string | null
  claimed_source_table: string | null
  approved_confidence: number | null
  actual_confidence: number | null
  claimed_confidence: number | null
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

interface ReviewDraft {
  edited_value: string
  officer_comment: string
}

async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    let detail = `Request failed with ${response.status}`
    try {
      const payload = await response.json()
      detail = payload.detail || detail
    } catch {
      detail = await response.text()
    }
    throw new Error(detail)
  }
  return response.json()
}

function fmtMoney(value: number | null | undefined) {
  return value == null ? '-' : value.toFixed(2)
}

function fmtPercent(value: number | null | undefined) {
  return value == null ? '-' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}

function confidenceClass(value: number | null | undefined) {
  if ((value ?? 0) >= 0.8) return 'bg-emerald-100 text-emerald-800'
  if ((value ?? 0) >= 0.6) return 'bg-amber-100 text-amber-800'
  return 'bg-red-100 text-red-800'
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('arr-upload')
  const [documents, setDocuments] = useState<Document[]>([])
  const [arrFile, setArrFile] = useState<File | null>(null)
  const [petitionFile, setPetitionFile] = useState<File | null>(null)
  const [extractions, setExtractions] = useState<Record<string, ExtractionResult>>({})
  const [comparison, setComparison] = useState<ComparisonResult | null>(null)
  const [order, setOrder] = useState<GeneratedOrder | null>(null)
  const [reviewDrafts, setReviewDrafts] = useState<Record<string, ReviewDraft>>({})
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const latestArr = useMemo(
    () => documents.find((doc) => doc.doc_type === 'arr_order'),
    [documents],
  )
  const latestPetition = useMemo(
    () => documents.find((doc) => doc.doc_type === 'truing_up_petition'),
    [documents],
  )
  const arrExtraction = latestArr ? extractions[latestArr.id] : null
  const petitionExtraction = latestPetition ? extractions[latestPetition.id] : null
  const canCompare = latestArr?.status === 'extracted' && latestPetition?.status === 'extracted'
  const reportUrl = order ? `http://127.0.0.1:8000${order.download_url}` : null

  useEffect(() => {
    loadAll().catch((err) => setError((err as Error).message))
  }, [])

  async function loadAll() {
    setError(null)
    const docs = await apiJson<Document[]>('/documents')
    setDocuments(docs)

    const latestByType = [
      docs.find((doc) => doc.doc_type === 'arr_order' && doc.status === 'extracted'),
      docs.find((doc) => doc.doc_type === 'truing_up_petition' && doc.status === 'extracted'),
    ].filter(Boolean) as Document[]

    const loadedExtractions: Record<string, ExtractionResult> = {}
    await Promise.all(latestByType.map(async (doc) => {
      loadedExtractions[doc.id] = await apiJson<ExtractionResult>(`/extraction/${doc.id}`)
    }))
    setExtractions((current) => ({ ...current, ...loadedExtractions }))

    try {
      const latestComparison = await apiJson<ComparisonResult>('/comparison/latest?financial_year=2024-25')
      setComparison(latestComparison)
    } catch {
      setComparison(null)
    }
  }

  async function uploadDocument(docType: DocType) {
    const file = docType === 'arr_order' ? arrFile : petitionFile
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)
    formData.append('financial_year', '2024-25')

    setLoading(docType)
    setError(null)
    setNotice(null)
    try {
      const endpoint = docType === 'arr_order' ? '/upload/arr' : '/upload/petition'
      const result = await apiJson<UploadResponse>(endpoint, { method: 'POST', body: formData })
      if (docType === 'arr_order') {
        setArrFile(null)
        setActiveTab('petition-upload')
      } else {
        setPetitionFile(null)
        setActiveTab(result.case_id ? 'comparison' : 'extraction')
      }
      setNotice(`${result.filename} uploaded and extracted (${result.rows_extracted} rows).`)
      await loadAll()
      await loadExtraction(result.id)
      if (result.case_id) await loadComparison(result.case_id)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(null)
    }
  }

  async function loadExtraction(documentId: string) {
    const result = await apiJson<ExtractionResult>(`/extraction/${documentId}`)
    setExtractions((current) => ({ ...current, [documentId]: result }))
  }

  async function runExtraction(documentId: string) {
    setLoading(`extract-${documentId}`)
    setError(null)
    try {
      const result = await apiJson<ExtractionResult>(`/extraction/${documentId}/run`, { method: 'POST' })
      setExtractions((current) => ({ ...current, [documentId]: result }))
      await loadAll()
      setActiveTab('extraction')
      setNotice(`${result.filename} extraction refreshed (${result.total_rows_extracted} rows).`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(null)
    }
  }

  async function runComparison() {
    setLoading('comparison')
    setError(null)
    try {
      const result = await apiJson<ComparisonResult>('/comparison/run?financial_year=2024-25', {
        method: 'POST',
      })
      setComparison(result)
      setActiveTab('comparison')
      setNotice(`Comparison generated for ${result.total_items} line items.`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(null)
    }
  }

  async function loadComparison(caseId: string) {
    const result = await apiJson<ComparisonResult>(`/comparison/${caseId}`)
    setComparison(result)
  }

  function updateReviewDraft(item: ComparisonItem, patch: Partial<ReviewDraft>) {
    setReviewDrafts((current) => ({
      ...current,
      [item.id]: {
        edited_value: current[item.id]?.edited_value ?? String(item.actual_value ?? ''),
        officer_comment: current[item.id]?.officer_comment ?? item.latest_review_comment ?? '',
        ...patch,
      },
    }))
  }

  async function saveReview(item: ComparisonItem, action: 'approve' | 'reject' | 'edit') {
    if (!comparison) return

    const draft = reviewDrafts[item.id] ?? {
      edited_value: String(item.actual_value ?? ''),
      officer_comment: item.latest_review_comment ?? '',
    }
    const editedValue = Number(draft.edited_value)

    setLoading(`review-${item.id}-${action}`)
    setError(null)
    try {
      await apiJson(`/review/${item.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          officer_name: 'Demo Officer',
          officer_comment: draft.officer_comment || `${action} by officer`,
          edited_value: action === 'edit' && Number.isFinite(editedValue) ? editedValue : undefined,
        }),
      })
      await loadComparison(comparison.case_id)
      setNotice('Review saved.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(null)
    }
  }

  async function generateOrder() {
    if (!comparison) return

    setLoading('generate')
    setError(null)
    try {
      const result = await apiJson<GeneratedOrder>('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_id: comparison.case_id,
          financial_year: comparison.financial_year,
          officer_name: 'Demo Officer',
        }),
      })
      setOrder(result)
      setActiveTab('generate')
      setNotice('Draft PDF generated.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(null)
    }
  }

  function documentList(docType: DocType) {
    const filtered = documents.filter((doc) => doc.doc_type === docType)
    if (!filtered.length) {
      return <p className="text-sm italic text-slate-500">No documents uploaded.</p>
    }

    return (
      <div className="space-y-3">
        {filtered.slice(0, 5).map((doc) => (
          <div key={doc.id} className="flex flex-col gap-3 rounded-md border border-slate-200 bg-slate-50 p-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-semibold text-slate-900">{doc.filename}</p>
              <p className="text-sm text-slate-600">
                {(doc.file_size / 1024 / 1024).toFixed(2)} MB | {doc.page_count ?? '-'} pages | {doc.status}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                className="kserc-button-secondary inline-flex items-center gap-2"
                onClick={async () => {
                  await loadExtraction(doc.id)
                  setActiveTab('extraction')
                }}
              >
                <Eye size={16} /> View Extraction
              </button>
              <button
                className="kserc-button inline-flex items-center gap-2 disabled:bg-slate-400"
                disabled={loading === `extract-${doc.id}`}
                onClick={() => runExtraction(doc.id)}
              >
                {loading === `extract-${doc.id}` ? <Loader2 className="animate-spin" size={16} /> : <RefreshCw size={16} />}
                Extract
              </button>
            </div>
          </div>
        ))}
        {filtered.length > 5 && (
          <p className="text-xs text-slate-500">Showing latest 5 of {filtered.length} uploaded documents.</p>
        )}
      </div>
    )
  }

  function uploadTab(docType: DocType) {
    const isArr = docType === 'arr_order'
    const file = isArr ? arrFile : petitionFile
    const setFile = isArr ? setArrFile : setPetitionFile
    const title = isArr ? 'Step 1: Upload ARR Approval Order' : 'Step 2: Upload 2024-25 Petition'
    const documentsTitle = isArr ? 'ARR Documents' : 'Petition Documents'

    return (
      <section className="mx-auto max-w-5xl px-6">
        <div className="kserc-card">
          <div className="mb-6 flex items-center justify-between gap-4">
            <h2 className="text-2xl font-bold">{title}</h2>
            <span className="rounded-md bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">FY 2024-25</span>
          </div>
          <div className="rounded-md border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center">
            <input
              id={`${docType}-file`}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            <label htmlFor={`${docType}-file`} className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700">
              <Upload size={18} /> Choose PDF
            </label>
            {file && (
              <div className="mt-5">
                <p className="text-sm text-slate-700">{file.name}</p>
                <button
                  className="mt-3 inline-flex items-center gap-2 rounded-md bg-emerald-600 px-5 py-2 font-semibold text-white hover:bg-emerald-700 disabled:bg-slate-400"
                  disabled={loading === docType}
                  onClick={() => uploadDocument(docType)}
                >
                  {loading === docType ? <Loader2 className="animate-spin" size={18} /> : <FileText size={18} />}
                  Upload and Extract
                </button>
              </div>
            )}
          </div>
          <div className="mt-8">
            <h3 className="mb-4 border-b border-slate-200 pb-2 text-lg font-semibold">{documentsTitle}</h3>
            {documentList(docType)}
          </div>
        </div>
      </section>
    )
  }

  function extractionPanel(title: string, result: ExtractionResult | null) {
    return (
      <div className="rounded-md border border-slate-200 bg-white p-4">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">{title}</h3>
            {result && <p className="text-sm text-slate-600">{result.filename}</p>}
          </div>
          {result && (
            <span className="rounded-md bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-700">
              {result.total_rows_extracted} rows
            </span>
          )}
        </div>
        {!result ? (
          <p className="text-sm text-slate-500">No extracted rows loaded.</p>
        ) : (
          <div className="max-h-[520px] overflow-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead className="sticky top-0 bg-slate-100">
                <tr>
                  <th className="border border-slate-200 px-3 py-2 text-left">Raw Label</th>
                  <th className="border border-slate-200 px-3 py-2 text-left">Normalized</th>
                  <th className="border border-slate-200 px-3 py-2 text-right">Value</th>
                  <th className="border border-slate-200 px-3 py-2 text-center">Type</th>
                  <th className="border border-slate-200 px-3 py-2 text-center">Confidence</th>
                  <th className="border border-slate-200 px-3 py-2 text-center">Source</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row) => (
                  <tr key={row.id}>
                    <td className="border border-slate-200 px-3 py-2">{row.row_label}</td>
                    <td className="border border-slate-200 px-3 py-2">{row.normalized_label}</td>
                    <td className="border border-slate-200 px-3 py-2 text-right">{fmtMoney(row.value)}</td>
                    <td className="border border-slate-200 px-3 py-2 text-center uppercase">{row.value_type}</td>
                    <td className="border border-slate-200 px-3 py-2 text-center">
                      <span className={`rounded px-2 py-1 text-xs font-semibold ${confidenceClass(row.confidence)}`}>
                        {(row.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="border border-slate-200 px-3 py-2 text-center">p.{row.page_number}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  function extractionTab() {
    return (
      <section className="mx-auto max-w-7xl px-6">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 className="text-2xl font-bold">Extraction Results</h2>
          <button
            className="kserc-button inline-flex items-center justify-center gap-2 disabled:bg-slate-400"
            disabled={!canCompare || loading === 'comparison'}
            onClick={runComparison}
          >
            {loading === 'comparison' ? <Loader2 className="animate-spin" size={18} /> : <RefreshCw size={18} />}
            Run Comparison
          </button>
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          {extractionPanel('ARR Approval Order', arrExtraction)}
          {extractionPanel('Petition', petitionExtraction)}
        </div>
      </section>
    )
  }

  function comparisonTab() {
    return (
      <section className="mx-auto max-w-7xl px-6">
        <div className="kserc-card">
          <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <h2 className="text-2xl font-bold">Comparison and Review Workbench</h2>
            <button
              className="rounded-md bg-emerald-600 px-5 py-2 font-semibold text-white hover:bg-emerald-700 disabled:bg-slate-400"
              disabled={!comparison || loading === 'generate'}
              onClick={generateOrder}
            >
              <span className="inline-flex items-center gap-2">
                {loading === 'generate' ? <Loader2 className="animate-spin" size={18} /> : <Download size={18} />}
                Generate PDF
              </span>
            </button>
          </div>
          {!comparison ? (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-8 text-center">
              <p className="mb-4 text-slate-600">Upload and extract both documents, then run comparison.</p>
              <button className="kserc-button" disabled={!canCompare} onClick={runComparison}>Run Comparison</button>
            </div>
          ) : (
            <>
              <div className="mb-6 grid gap-4 md:grid-cols-4">
                <Metric label="Total Items" value={comparison.total_items} />
                <Metric label="AI Auto" value={comparison.auto_approved} tone="green" />
                <Metric label="Review Required" value={comparison.review_required} tone="amber" />
                <Metric label="Total Variance" value={`${comparison.total_variance.toFixed(2)} Cr.`} tone="blue" />
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-[1400px] border-collapse text-sm">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className="border border-slate-200 px-3 py-2 text-left">Line Item</th>
                      <th className="border border-slate-200 px-3 py-2 text-right">ARR Approved</th>
                      <th className="border border-slate-200 px-3 py-2 text-right">Actual</th>
                      <th className="border border-slate-200 px-3 py-2 text-right">Claimed</th>
                      <th className="border border-slate-200 px-3 py-2 text-right">Variance</th>
                      <th className="border border-slate-200 px-3 py-2 text-right">Variance %</th>
                      <th className="border border-slate-200 px-3 py-2 text-left">Traceability</th>
                      <th className="border border-slate-200 px-3 py-2 text-left">Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.items.map((item) => {
                      const draft = reviewDrafts[item.id] ?? {
                        edited_value: String(item.actual_value ?? ''),
                        officer_comment: item.latest_review_comment ?? '',
                      }
                      const isReview = item.decision_class !== 'AI_AUTO'
                      return (
                        <tr key={item.id} className={isReview ? 'bg-amber-50' : 'bg-emerald-50'}>
                          <td className="border border-slate-200 px-3 py-2 align-top">
                            <p className="font-semibold text-slate-900">{item.canonical_name}</p>
                            <p className="text-xs text-slate-500">{item.cost_head ?? 'Other'}</p>
                            {item.flag_reason && <p className="mt-1 text-xs text-slate-600">{item.flag_reason}</p>}
                          </td>
                          <td className="border border-slate-200 px-3 py-2 text-right align-top">{fmtMoney(item.approved_value)}</td>
                          <td className="border border-slate-200 px-3 py-2 text-right align-top">
                            <input
                              className="w-28 rounded border border-slate-300 px-2 py-1 text-right"
                              value={draft.edited_value}
                              onChange={(event) => updateReviewDraft(item, { edited_value: event.target.value })}
                            />
                          </td>
                          <td className="border border-slate-200 px-3 py-2 text-right align-top">{fmtMoney(item.claimed_value)}</td>
                          <td className={`border border-slate-200 px-3 py-2 text-right align-top ${item.variance && item.variance > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                            {fmtMoney(item.variance)}
                          </td>
                          <td className={`border border-slate-200 px-3 py-2 text-right align-top ${item.variance_percent && item.variance_percent > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                            {fmtPercent(item.variance_percent)}
                          </td>
                          <td className="border border-slate-200 px-3 py-2 align-top text-xs text-slate-700">
                            <p>ARR p.{item.approved_source_page ?? '-'}</p>
                            <p>Petition actual p.{item.actual_source_page ?? '-'}</p>
                            <p>Claimed p.{item.claimed_source_page ?? '-'}</p>
                            <p className="mt-1">Conf: ARR {item.approved_confidence ? `${(item.approved_confidence * 100).toFixed(0)}%` : '-'}, Petition {item.actual_confidence ? `${(item.actual_confidence * 100).toFixed(0)}%` : '-'}</p>
                          </td>
                          <td className="border border-slate-200 px-3 py-2 align-top">
                            <textarea
                              className="mb-2 h-16 w-64 rounded border border-slate-300 px-2 py-1"
                              placeholder="Officer note"
                              value={draft.officer_comment}
                              onChange={(event) => updateReviewDraft(item, { officer_comment: event.target.value })}
                            />
                            <div className="flex flex-wrap gap-2">
                              <button className="rounded bg-emerald-600 px-2 py-1 text-xs font-semibold text-white" onClick={() => saveReview(item, 'approve')}>
                                <Check size={14} className="inline" /> Approve
                              </button>
                              <button className="rounded bg-blue-600 px-2 py-1 text-xs font-semibold text-white" onClick={() => saveReview(item, 'edit')}>
                                <Edit3 size={14} className="inline" /> Save Edit
                              </button>
                              <button className="rounded bg-red-600 px-2 py-1 text-xs font-semibold text-white" onClick={() => saveReview(item, 'reject')}>
                                <X size={14} className="inline" /> Reject
                              </button>
                            </div>
                            {item.latest_review_action && (
                              <p className="mt-2 text-xs text-slate-600">Saved: {item.latest_review_action}</p>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </section>
    )
  }

  function generateTab() {
    return (
      <section className="mx-auto max-w-6xl px-6">
        <div className="kserc-card">
          <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <h2 className="text-2xl font-bold">Generated KSERC Draft Order</h2>
            {reportUrl && (
              <a className="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-700" href={reportUrl} target="_blank" rel="noreferrer">
                <Download size={18} /> Download PDF
              </a>
            )}
          </div>
          {!order ? (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-8 text-center">
              <p className="mb-4 text-slate-600">Generate a draft after comparison review.</p>
              <button className="kserc-button" disabled={!comparison || loading === 'generate'} onClick={generateOrder}>
                {loading === 'generate' ? 'Generating...' : 'Generate Draft PDF'}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                Draft generated for case {order.case_id}. File size: {(order.file_size / 1024).toFixed(1)} KB.
              </div>
              {reportUrl && <iframe title="KSERC Draft PDF Preview" src={reportUrl} className="h-[760px] w-full rounded-md border border-slate-300" />}
            </div>
          )}
        </div>
      </section>
    )
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-5 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-950">KSERC Decision Support System</h1>
            <p className="text-sm text-slate-600">Demo MVP | ARR vs Petition truing-up workflow</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-semibold">
            <StatusPill label="ARR" ok={latestArr?.status === 'extracted'} />
            <StatusPill label="Petition" ok={latestPetition?.status === 'extracted'} />
            <StatusPill label="Comparison" ok={!!comparison} />
            <StatusPill label="PDF" ok={!!order} />
          </div>
        </div>
      </header>

      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl overflow-x-auto px-6">
          {[
            ['arr-upload', 'ARR Upload'],
            ['petition-upload', 'Petition Upload'],
            ['extraction', 'Extraction'],
            ['comparison', 'Comparison & Review'],
            ['generate', 'PDF Preview'],
          ].map(([id, label]) => (
            <button
              key={id}
              className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-semibold ${activeTab === id ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-600 hover:text-slate-900'}`}
              onClick={() => setActiveTab(id as Tab)}
            >
              {label}
            </button>
          ))}
        </div>
      </nav>

      <main className="py-8">
        {(error || notice) && (
          <div className={`mx-auto mb-5 max-w-7xl rounded-md px-4 py-3 text-sm ${error ? 'border border-red-200 bg-red-50 text-red-800' : 'border border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
            {error || notice}
          </div>
        )}
        {activeTab === 'arr-upload' && uploadTab('arr_order')}
        {activeTab === 'petition-upload' && uploadTab('truing_up_petition')}
        {activeTab === 'extraction' && extractionTab()}
        {activeTab === 'comparison' && comparisonTab()}
        {activeTab === 'generate' && generateTab()}
      </main>
    </div>
  )
}

function Metric({ label, value, tone = 'slate' }: { label: string; value: string | number; tone?: 'slate' | 'green' | 'amber' | 'blue' }) {
  const classes = {
    slate: 'bg-slate-50 text-slate-900',
    green: 'bg-emerald-50 text-emerald-800',
    amber: 'bg-amber-50 text-amber-800',
    blue: 'bg-blue-50 text-blue-800',
  }[tone]
  return (
    <div className={`rounded-md border border-slate-200 p-4 ${classes}`}>
      <p className="text-sm font-semibold">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  )
}

function StatusPill({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className={`rounded-md px-3 py-1 ${ok ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}`}>
      {label}: {ok ? 'Ready' : 'Pending'}
    </span>
  )
}

export default App
