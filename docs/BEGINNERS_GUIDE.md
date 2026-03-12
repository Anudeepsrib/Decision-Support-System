# The Beginner's Guide: Deterministic Decision Support System

*A Plain-English Introduction for Supply Chain and Financial Auditors*

---

## What is this system?

Imagine receiving an **Invoice (Order PDF)** claiming you ordered 5,000 widgets for $3.50 each from Acme Corp. Now imagine looking at the original **Purchase Order (Reference PDF)** you sent them, which states you ordered 5,000 widgets for $3.15 each from Acme Corp.

Finding that singular missing 35-cent discrepancy by hand across thousands of multi-page PDF documents every day is exhausting, expensive, and error-prone. 

This system acts as a perfectly rigid, mathematical **AI Auditor** that reads those documents and compares them deterministically. 

## The "Zero Hallucination" Rule

Many modern tools simply ask chatbots like ChatGPT to "compare these two documents". The problem? Large Language Models (LLMs) hallucinate. They might accidentally read $3.15 as $3.50 because they are guessing probabilities, not doing math. 

This system is built from the ground up to **avoid LLM hallucination entirely**. 

**How it works without guessing:**
1. It strips the raw computer text character-for-character directly out of the PDFs.
2. It uses mathematical regular expressions (Regex) to map blocks like "Order Date:" or "Qty:".
3. It breaks tables apart using spacing heuristics. 
4. It compares strings. If the Order says "Acme Corporation" and the Reference says "Acme Corp.", it uses an algorithm called `difflib` to score the similarity. If the score is >= `0.70`, it mathematically declares a match.
5. If the Unit Prices deviate by more than ±1.0%, it mathematically declares a discrepancy.

**The result:** You can run the exact same two documents through the system 1,000 times and it will yield the exact same anomaly report 1,000 times in a row, every fraction of a second, without ever calling the internet.

## The Interface

When you upload your Order and Reference PDFs into the React Interface, it instantly returns:

1. **A Confidence Ring:** A score from 0-100 indicating how structurally sound the data was.
2. **Anomaly Distributions:** A bar chart showing exactly how many line items were a Perfect Match ✅, a Complete Mismatch ❌, Missing From Reference ⚠️, or Extra In Reference ℹ️.
3. **The Executive Table:** A side-by-side comparison isolating exactly which numerical cell failed the test (e.g., highlighting the $3.50 Unit Price failure in bright red so the human auditor can act instantly).

## (Optional) The LLM Executive Report
At the very end of the pipeline, **only after all the math is strictly finished**, the system *can* hand the final factual JSON matrix to OpenAI to write a quick, 3-paragraph English executive summary highlighting the risk posture. This is purely optional. If an internet connection/API Key is unavailable, the system silently pivots to building the exact same report natively utilizing pre-coded string formatting. 

## Wrap Up
This Decision Support System converts days of eye-straining PDF table verification into a 3-second, purely mathematical check-and-balance, empowering auditors to focus purely on escalating discrepancies rather than searching for them.
