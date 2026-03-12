"""
Unit tests for the Deterministic Order Comparator.
Tests regex parsing, date normalization, difflib item matching,
and rule-based discrepancy flagging without ANY LLM dependency.
"""

import pytest
import os
from unittest.mock import patch
from datetime import datetime, timezone

from backend.ai.OrderComparator import OrderComparator, extract_fields


MOCK_ORDER_TEXT = """
Order Number: ORD-2026-999
Customer: ACME Corp
Shipping Address: 123 Main St, New York
Date Ordered: 2026-03-01
Delivery Date: 2026-03-15

Qty    Product                Unit Price    Total
10     MacBook Pro 14-inch    1999.00       19990.00
5      Magic Mouse            79.00         395.00
"""

MOCK_REFERENCE_TEXT = """
PO Number: ORD-2026-999
Client: Acme Corporation
Deliver To: 123 Main St, New York
Order Date: 03/01/2026
Ship Date: 03/20/2026

Quantity  Item Description    Price      Total
10        MacBook Pro 14"     1999.00    19990.00
4         Magic Mouse         79.00      316.00
1         Keyboard            149.00     149.00
"""


class TestOrderComparatorDeterministic:
    """Tests for the fully deterministic OrderComparator engine."""

    def test_regex_extraction(self):
        """Test that regex correctly extracts fields from unstructured text."""
        fields = extract_fields(MOCK_ORDER_TEXT)
        assert fields["order_number"] == "ORD-2026-999"
        assert fields["customer_name"] == "ACME Corp"
        assert fields["order_date"] == "2026-03-01"
        assert len(fields["items"]) == 2
        assert fields["items"][0]["quantity"] == 10
        assert fields["items"][0]["unit_price"] == 1999.0
        assert "MacBook" in fields["items"][0]["product_name"]

    def test_deterministic_comparison(self):
        """Test full deterministic pipeline comparing order vs reference logic."""
        comparator = OrderComparator()
        result = comparator.compare(MOCK_ORDER_TEXT, MOCK_REFERENCE_TEXT)
        
        comp = result["comparison_result"]
        
        # Exact match (Order No)
        assert comp["order_level_comparison"]["order_number"]["status"] == "MATCH"
        
        # Similarity match (Customer)
        assert comp["order_level_comparison"]["customer_name"]["status"] == "MATCH"
        
        # Mismatch (Delivery Date)
        assert comp["order_level_comparison"]["delivery_date"]["status"] == "MISMATCH"
        
        # Item comparison
        items = comp["items_comparison"]
        assert len(items) == 2
        
        # Magic Mouse mismatch (qty 5 vs 4)
        mouse_item = next(i for i in items if "Mouse" in i["product_name_order"])
        assert mouse_item["status"] == "MISMATCH"
        assert "Quantity differs" in mouse_item["reason"]
        
        # MacBook match (difflib handles 14-inch vs 14")
        mb_item = next(i for i in items if "MacBook" in i["product_name_order"])
        assert mb_item["status"] == "MATCH"

        # Extra items reporting
        assert len(comp["extra_items_in_reference"]) == 1
        assert "Keyboard" in comp["extra_items_in_reference"][0]
        
        # Summary
        assert comp["summary"]["overall_status"] == "CRITICAL_DISCREPANCY"
        assert comp["summary"]["mismatched_items"] == "1"
        
        # Executive Report generated
        assert "Review discrepancies" in result["executive_report"] or "Reject or escalate" in result["executive_report"]

    @patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=True)
    def test_llm_report_disabled_when_no_api_key(self):
        """Ensure LLM report is smoothly skipped without a key."""
        comparator = OrderComparator()
        result = comparator.compare(MOCK_ORDER_TEXT, MOCK_REFERENCE_TEXT)
        assert result["llm_report"] == "LLM_REPORT_DISABLED"

    @patch("langchain_openai.ChatOpenAI")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"})
    def test_llm_report_runs_if_api_key_present(self, mock_chat_cls):
        """Ensure LLM report runs if key is present."""
        class MockLLMResponse:
            content = "Mocked LLM Analysis"
            
        mock_model = mock_chat_cls.return_value
        mock_model.invoke.return_value = MockLLMResponse()
        
        comparator = OrderComparator()
        result = comparator.compare(MOCK_ORDER_TEXT, MOCK_REFERENCE_TEXT)
        assert result["llm_report"] == "Mocked LLM Analysis"
