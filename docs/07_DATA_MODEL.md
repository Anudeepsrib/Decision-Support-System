# KSERC Decision Support System — Data Model

**Source:** `backend/models.py` (SQLAlchemy declarative)

**Database:** SQLite by default (`data/kserc_dss.db`). Other SQLAlchemy-compatible engines are accepted via `DATABASE_URL` but have not been validated in the MVP.

---

## Entity Relationship Overview

```
Document (1) ────< (many) ExtractedRow
Document (1) ────< (many) ExtractionJob
ExtractedRow (1) ────< (0..1) NormalizedLineItem
NormalizedLineItem (many) ──► Comparison (via canonical mapping)
Comparison (1) ────< (0..1) Review
Comparison (many) ──► GeneratedOrder (via case_id)
```

---

## Table Specifications

### 1. documents

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | String(36) PK | No | UUID4 |
| filename | String(255) | No | Original filename |
| doc_type | String(50) | No | "arr_order" \| "truing_up_petition" |
| financial_year | String(10) | No | "2024-25" (inferred or default) |
| file_path | String(500) | No | Absolute or relative path on disk |
| file_size | Integer | No | Bytes |
| page_count | Integer | Yes | From pdfplumber |
| upload_timestamp | DateTime | Yes | UTC |
| status | String(20) | Yes | "uploaded" \| "extracted" \| "processed" |

**Relationships:** `extracted_rows`, `extraction_jobs`

---

### 2. extraction_jobs

Tracks background extraction progress (polled by frontend).

| Column | Type | Description |
|--------|------|-------------|
| id | String(36) PK | Job UUID |
| document_id | FK → documents.id | |
| status | String(20) | PENDING \| PROCESSING \| COMPLETED \| FAILED |
| stage | String(200) | Human-readable stage ("Extracting page 47...", etc.) |
| progress | Float | 0.0–1.0 |
| processed_pages | Integer | |
| total_pages | Integer | Nullable |
| rows_extracted | Integer | |
| case_id | String(36) | Populated after successful comparison |
| error_message | Text | |
| created_at / started_at / completed_at | DateTime | |

**Index:** `ix_extraction_job_doc_created`

---

### 3. extracted_rows

Raw rows from pdfplumber with full provenance.

| Column | Type | Description |
|--------|------|-------------|
| id | String(36) PK | |
| document_id | FK | |
| page_number | Integer | 1-based |
| table_index | Integer | Index within page |
| table_name | String(200) | Detected caption / title |
| row_label | String(300) | Raw text from first column |
| value | Float | Nullable (parsing failures become NULL) |
| value_type | String(20) | "approved" \| "actual" \| "claimed" \| "value" |
| unit | String(20) | "Rs. Cr." (default), "MU", "%", etc. |
| confidence | Float | 0.0–1.0 (heuristic) |
| extraction_method | String(50) | "pdfplumber" (primary) |
| raw_text | Text | Full cell text for debugging |
| extracted_at | DateTime | |

**Index:** `ix_extracted_doc_page`

**Note:** This table is the source of truth for "where did this number come from?"

---

### 4. normalized_line_items

After canonical mapping (the bridge to comparison).

| Column | Type | Description |
|--------|------|-------------|
| id | String(36) PK | |
| extracted_row_id | FK (nullable) | |
| canonical_name | String(200) | e.g. "Power Purchase Cost" |
| category | String(50) | "ARR" \| "ERC" \| "Revenue_Gap" etc. |
| cost_head | String(50) | O&M, Power_Purchase, Interest... |
| source_doc_type | String(50) | "arr_order" \| "truing_up_petition" |
| financial_year | String(10) | |
| value_type | String(20) | "actual" \| "claimed" \| "approved" |
| value | Float | |
| unit | String(20) | |
| mapping_confidence | Float | 1.0 for rule-based in MVP |
| mapping_method | String(50) | "rule_based" (MVP) \| "ai_semantic" (future) |
| created_at | DateTime | |

**Indexes:** `ix_norm_canonical_year`, `ix_norm_doc_type`

---

### 5. comparisons

The heart of the MVP — three-way variance view.

| Column | Type | Description |
|--------|------|-------------|
| id | String(36) PK | |
| case_id | String(36) | Groups one ARR + one Petition run |
| financial_year | String(10) | |
| canonical_id | String(100) | From registry (e.g. "PURCHASE_OF_POWER") |
| canonical_name | String(200) | Display name |
| display_name | String(200) | |
| sbu | String(20) | "SBU-G" \| "SBU-T" \| "SBU-D" \| ... |
| unit | String(20) | |
| section | String(50) | Registry section |
| cost_head | String(50) | |
| approved_value | Float | From ARR Order |
| actual_value | Float | From Petition |
| claimed_value | Float | From Petition (utility ask) |
| variance | Float | actual - approved (or claimed fallback) |
| variance_percent | Float | (variance / \|approved\|) * 100 |
| decision_class | String(30) | ACCEPTABLE_VARIANCE \| REVIEW_REQUIRED \| INCOMPLETE_DATA |
| flag_reason | String(200) | |
| approved/actual/claimed_source_document_id | String(36) | Provenance |
| approved/actual/claimed_source_page | Integer | |
| approved/actual/claimed_source_table | String(200) | |
| approved/actual/claimed_confidence | Float | |
| created_at | DateTime | |

**Index:** `ix_comparison_case`

**Fallback rule** (implemented in comparison + report_context):
- If actual_value is missing but claimed_value exists → use claimed_value for variance calculation.

---

### 6. reviews

Officer decisions on comparison items.

| Column | Type | Description |
|--------|------|-------------|
| id | String(36) PK | |
| comparison_id | FK → comparisons.id | |
| action | String(20) | "approve" \| "reject" \| "edit" |
| officer_name | String(100) | "Demo Officer" in demo mode |
| officer_comment | Text | Mandatory free-text justification |
| edited_value | Float | Only when action="edit" |
| ai_explanation | Text | Actually holds the deterministic template text from prompts.py (column name kept for compatibility) |
| reviewed_at | DateTime | |

---

### 7. generated_orders

Metadata for every PDF produced.

| Column | Type | Description |
|--------|------|-------------|
| id | String(36) PK | |
| case_id | String(36) | Links back to the comparison set |
| financial_year | String(10) | |
| file_path | String(500) | Absolute path in output/ |
| file_hash | String(64) | SHA-256 of the PDF bytes |
| file_size | Integer | |
| is_draft | Boolean | Always true in MVP |
| watermark_text | String(100) | "DRAFT GENERATED FOR REVIEW" |
| total_items / auto_approved / review_required | Integer | Snapshot at generation time |
| generated_by | String(100) | "system" |
| generated_at | DateTime | |

---

## Important Constraints & Notes

1. **No foreign key enforcement on SQLite** for some relationships (performance in demo). The application maintains integrity via Python logic.
2. **NormalizedLineItem** is the only place where "ai_semantic" mapping_method could appear in future; currently always "rule_based".
3. **case_id** is the primary correlation key between a set of documents, their comparisons, reviews, and the generated order.
4. **Provenance columns** (source_page, source_table, source_document_id) on `comparisons` are the foundation of auditability. The PDF generator and report context deliberately expose these in appendices.
5. **No user table** in the MVP. Authentication is stubbed (DEMO_MODE bypasses it). A real `users` / `roles` table will appear in Phase 3.

---

## Example Row (Conceptual)

**comparisons** row for "Power Purchase Cost" (SBU-D):

```json
{
  "canonical_id": "PURCHASE_OF_POWER",
  "canonical_name": "Purchase of Power",
  "sbu": "SBU-D",
  "approved_value": 12450.75,
  "actual_value": 13120.40,
  "claimed_value": 13200.00,
  "variance": 669.65,
  "variance_percent": 5.38,
  "decision_class": "ACCEPTABLE_VARIANCE",
  "approved_source_page": 47,
  "actual_source_page": 112,
  "flag_reason": null
}
```

This row is what eventually appears in Chapter-5 tables of the generated PDF.

---

See [08_EXTRACTION_PIPELINE.md](08_EXTRACTION_PIPELINE.md) for how `extracted_rows` become `normalized_line_items`, and [10_COMPARISON_ENGINE.md](10_COMPARISON_ENGINE.md) for how `comparisons` are populated.
