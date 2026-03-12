"""
CLI Entrypoint: Order vs Reference Document Comparison
Usage: python compare.py order.pdf reference.pdf

Outputs:
  - comparison_result.json   (structured JSON comparison)
  - comparison_report.txt    (plain-text report, always generated)
  - comparison_report_llm.txt (LLM report, only if OPENAI_API_KEY is set)

Fully deterministic — no LLM needed for comparison.
"""

import sys
import json
import io
from pathlib import Path

import PyPDF2

from backend.ai.OrderComparator import OrderComparator


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF file using PyPDF2."""
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    if not path.suffix.lower() == ".pdf":
        print(f"ERROR: File must be a PDF: {filepath}")
        sys.exit(1)

    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        pages = {}
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages[i + 1] = text

    combined = "\n\n".join(
        f"--- Page {num} ---\n{text}"
        for num, text in sorted(pages.items())
    )

    if len(combined.strip()) < 10:
        print(f"WARNING: Very little text extracted from {filepath}. File may be scanned/image-based.")
        print("         For scanned PDFs, use the web API which supports OCR fallback.")

    return combined


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare.py <order.pdf> <reference.pdf>")
        print()
        print("Outputs:")
        print("  comparison_result.json    — Structured JSON comparison")
        print("  comparison_report.txt     — Plain-text deterministic report")
        print("  comparison_report_llm.txt — LLM report (if OPENAI_API_KEY is set)")
        sys.exit(1)

    order_path = sys.argv[1]
    reference_path = sys.argv[2]

    print(f"📄 Order:     {order_path}")
    print(f"📑 Reference: {reference_path}")
    print()

    # Step 1: Extract text
    print("🔍 Extracting text from PDFs...")
    order_text = extract_text_from_pdf(order_path)
    reference_text = extract_text_from_pdf(reference_path)
    print(f"   Order:     {len(order_text)} characters extracted")
    print(f"   Reference: {len(reference_text)} characters extracted")
    print()

    # Step 2: Run deterministic comparison
    print("⚙️  Running deterministic comparison...")
    comparator = OrderComparator()
    result = comparator.compare(order_text, reference_text)
    print("   ✅ Comparison complete")
    print()

    # Step 3: Write outputs
    comparison = result["comparison_result"]
    summary = comparison.get("summary", {})

    # JSON output
    json_path = "comparison_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    print(f"📊 JSON output:  {json_path}")

    # Plain-text report
    report_path = "comparison_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result["executive_report"])
    print(f"📝 Report:       {report_path}")

    # LLM report (optional)
    llm_report = result.get("llm_report", "LLM_REPORT_DISABLED")
    if llm_report and llm_report != "LLM_REPORT_DISABLED" and not llm_report.startswith("LLM_REPORT_ERROR"):
        llm_path = "comparison_report_llm.txt"
        with open(llm_path, "w", encoding="utf-8") as f:
            f.write(llm_report)
        print(f"🤖 LLM Report:   {llm_path}")
    else:
        print(f"🤖 LLM Report:   {llm_report}")

    print()

    # Step 4: Print summary
    total = summary.get("total_items_order", "0")
    matched = summary.get("matched_items", "0")
    mismatched = summary.get("mismatched_items", "0")
    missing = summary.get("missing_items", "0")
    extra = summary.get("extra_items", "0")
    overall = summary.get("overall_status", "UNKNOWN")
    confidence = comparison.get("confidence_score", "?")

    print("=" * 50)
    print("  COMPARISON SUMMARY")
    print("=" * 50)
    print(f"  Total Items:      {total}")
    print(f"  ✅ Matched:       {matched}")
    print(f"  ❌ Mismatched:    {mismatched}")
    print(f"  ⚠️  Missing:       {missing}")
    print(f"  ℹ️  Extra:         {extra}")
    print(f"  📊 Confidence:    {confidence}%")
    print(f"  🏷️  Status:        {overall}")
    print("=" * 50)


if __name__ == "__main__":
    main()
