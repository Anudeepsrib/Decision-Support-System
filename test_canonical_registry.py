#!/usr/bin/env python3
"""
Test canonical registry mapping and tariff/noise filtering.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from canonical_registry import canonicalize_records, map_record_to_canonical


def test_registry_mapping():
    records = [
        {"raw_label": "Power Purchase Cost", "value": 100.0},
        {"raw_label": "A&G Expenses", "value": 10.0},
        {"raw_label": "Return on Equity", "value": 5.0},
        {"raw_label": "Energy Sales", "value": 15000.0},
    ]
    mapped = canonicalize_records(records)
    ids = {record["canonical_id"] for record in mapped}
    assert "PURCHASE_OF_POWER" in ids
    assert "OM_COST" in ids
    assert "ROE" in ids
    assert "ENERGY_SALES" in ids
    print("PASS registry maps MVP financial line items")


def test_tariff_filtering():
    tariff_rows = [
        {"raw_label": "0 to 100 units", "table_name": "Tariff Schedule", "value": 3.5},
        {"raw_label": "Single phase fixed charge", "value": 80.0},
        {"raw_label": "Energy charge per unit", "value": 6.0},
    ]
    for record in tariff_rows:
        assert map_record_to_canonical(record) is None
    print("PASS tariff slabs and charge rows are excluded")


if __name__ == "__main__":
    test_registry_mapping()
    test_tariff_filtering()
    print("Canonical registry tests passed.")
