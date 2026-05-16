# KSERC Decision Support System — Frontend Workflow

**Main file:** `frontend/src/App.tsx`  
**Tech:** Vite + React 18 + TypeScript + Tailwind + lucide-react icons + axios

---

## Tab Structure (Exact Order in UI)

The single-page app uses a `Tab` union type:

```ts
type Tab = 'arr-upload' | 'petition-upload' | 'extraction' | 'comparison' | 'generate'
```

### 1. ARR Upload Tab (`arr-upload`)

- Drag-and-drop or file input for `.pdf`
- Only one ARR document per case (enforced)
- After upload: shows `DocumentUploadResponse` with job status
- Auto-polls extraction job until `COMPLETED`
- Displays: filename, page count, rows extracted, status

### 2. Petition Upload Tab (`petition-upload`)

- Same UX as ARR
- Separate document type
- Both documents must be present before "Run Comparison" becomes available

### 3. Extraction Tab (`extraction`)

- Shows side-by-side (or tabbed) results for ARR and Petition
- "Run Comparison" button appears only when both documents have `status === 'extracted'`
- Button calls `POST /api/comparison/run`
- Shows extraction stats: total rows, rows needing review, method (pdfplumber)

### 4. Comparison Tab (`comparison`)

- Large table of all mapped canonical items
- Columns: #, Canonical Name, SBU, Approved, Actual, Claimed, Variance, %, Status, Source Pages, Actions
- Status badges:
  - Green: ACCEPTABLE_VARIANCE
  - Amber: REVIEW_REQUIRED
  - Red: INCOMPLETE_DATA
- Per-row actions: Approve / Edit Value / Reject + mandatory comment textarea
- "Submit Review" posts to `/api/review/{comparison_id}`
- Summary bar: Total items | Auto-approved | Review required | Incomplete

### 5. Generate Tab (`generate`)

- "Generate KSERC Draft Order" button
- Disabled while generation in progress (loading state)
- After success: shows order metadata + "Download PDF" + "Preview in Browser" (opens `/generated/...`)
- Also lists previously generated orders for the case

---

## Key State Management Patterns

- `documents` array — all uploaded docs with their latest job status
- `extraction` — latest extraction result (can be ARR or Petition)
- `comparison` — full `ComparisonResponse` (the authoritative source for the comparison table)
- `reviews` — map of comparison_id → ReviewResponse (local cache)
- `generating`, `comparing` — loading flags to prevent duplicate clicks

The frontend does **not** maintain the source of truth; it is a view layer over the backend DB.

---

## API Calls Made by the Frontend

- `POST /api/upload/arr`
- `POST /api/upload/petition`
- `GET /api/job/{job_id}` (polling)
- `GET /api/extraction/{doc_id}`
- `POST /api/comparison/run?financial_year=...`
- `GET /api/comparison/results`
- `POST /api/review/{id}`
- `POST /api/generate`
- `GET /api/generate/{order_id}/download` (or direct static link)

All calls go through the `API_BASE` constructed in `App.tsx`:

```ts
const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'
```

---

## User Experience Safeguards (Current)

- Upload only accepts `.pdf`
- Max size 75 MB (enforced server-side)
- Review comment is required before submit (client + server)
- Generate button is always available (even with pending reviews) — this is intentional for demo flow (see QA report history)
- Clear error banners for extraction failure, comparison failure, PDF generation failure

---

## Known Frontend Limitations

1. Single extraction result object in state — viewing ARR extraction overwrites petition view (mitigated by the documents list)
2. No real-time collaboration or multi-user
3. No PDF preview pane inside the app (opens in new tab)
4. TOC page numbers in generated PDF are approximate
5. No "undo review" flow (would require additional backend support)

---

## How to Run the Frontend in Isolation (for UI work)

```bash
cd frontend
npm run dev   # or npm start
```

It will still need a running backend at the configured `VITE_API_BASE_URL`.

---

## Styling

- Tailwind via `tailwind.config.js`
- Custom components in `App.css` and `index.css`
- Icons from `lucide-react`

The UI is deliberately functional rather than pixel-perfect branded. Future Phase 3 work can add a proper design system.

---

See [15_DEMO_SCRIPT.md](15_DEMO_SCRIPT.md) for the exact sequence a presenter should walk through in the UI, including honest language about coverage.
