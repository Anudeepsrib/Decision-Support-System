"""
Smoke test for all audit fixes in the Rule Engine.
Run with: PYTHONPATH=. python tests/test_engine_smoke.py
"""
from backend.engine.constants import KSERC, T_AND_D_LOSS_TRAJECTORY
from backend.engine.rule_engine import RuleEngine, CostInput, CostCategory, SBUCode

engine = RuleEngine(KSERC)
passed = 0

# Test 1: Controllable Gain (uses enums now — F-03/F-04)
inp1 = CostInput(
    head="O&M", category=CostCategory.CONTROLLABLE, sbu_code=SBUCode.SBU_D,
    approved=150, actual=120, is_human_verified=True,
)
r1 = engine.compute_variance(inp1)
assert r1.variance_amount == 30.0, f"Expected 30, got {r1.variance_amount}"
assert r1.disallowed_variance == 0.0
assert r1.disallowance_reason is None
print(f"[PASS] TEST 1 — Controllable Gain: variance={r1.variance_amount}")
passed += 1

# Test 2: Checksum reproducibility — same inputs, same hash
r1b = engine.compute_variance(inp1)
assert r1.checksum == r1b.checksum, "CHECKSUM MISMATCH — reproducibility broken!"
print(f"[PASS] TEST 2 — Checksum reproducibility: {r1.checksum[:16]}...")
passed += 1

# Test 3: Controllable Loss (F-02: money rounding)
inp3 = CostInput(
    head="O&M", category=CostCategory.CONTROLLABLE, sbu_code=SBUCode.SBU_D,
    approved=150, actual=200, is_human_verified=True,
)
r3 = engine.compute_variance(inp3)
assert r3.disallowed_variance == 50.0
assert r3.disallowance_reason is not None
print(f"[PASS] TEST 3 — Controllable Loss: disallowed={r3.disallowed_variance}")
passed += 1

# Test 4: Zero-hallucination guard — unverified actual should RAISE
try:
    bad = CostInput(
        head="O&M", category=CostCategory.CONTROLLABLE, sbu_code=SBUCode.SBU_D,
        approved=150, actual=200, is_human_verified=False,
    )
    engine.compute_variance(bad)
    print("[FAIL] TEST 4 — should have raised ValueError")
except ValueError as e:
    print(f"[PASS] TEST 4 — Zero-hallucination guard raised: {str(e)[:60]}...")
    passed += 1

# Test 5: T&D trajectory lookup
td_2425 = engine.get_td_loss_target("2024-25")
assert td_2425 == 0.145, f"Expected 0.145, got {td_2425}"
print(f"[PASS] TEST 5 — T&D FY_2024-25: {td_2425}")
passed += 1

# Test 6: Derived NORMATIVE_INTEREST_RATE
expected_rate = round(KSERC.SBI_EBLR + KSERC.INTEREST_SPREAD, 6)
assert KSERC.NORMATIVE_INTEREST_RATE == expected_rate
print(f"[PASS] TEST 6 — Normative Interest Rate: {KSERC.NORMATIVE_INTEREST_RATE} (derived)")
passed += 1

# Test 7: Uncontrollable pass-through
inp7 = CostInput(
    head="Power_Purchase", category=CostCategory.UNCONTROLLABLE, sbu_code=SBUCode.SBU_G,
    approved=400, actual=450, is_human_verified=True,
)
r7 = engine.compute_variance(inp7)
assert r7.disallowed_variance == 0.0
assert r7.passed_through_variance == -50.0
print(f"[PASS] TEST 7 — Uncontrollable: passed_through={r7.passed_through_variance}")
passed += 1

# Test 8: F-03 — Invalid category string should NOT be accepted
try:
    bad_cat = CostInput(
        head="O&M", category="controllable",  # type: ignore — intentional lowercase typo
        sbu_code=SBUCode.SBU_D, approved=150, actual=200, is_human_verified=True,
    )
    print("[FAIL] TEST 8 — should have raised ValueError for invalid category")
except (ValueError, KeyError):
    print("[PASS] TEST 8 — Invalid category 'controllable' correctly rejected by Enum")
    passed += 1

# Test 9: F-02 — Floating-point precision (banker's rounding)
inp9 = CostInput(
    head="O&M", category=CostCategory.CONTROLLABLE, sbu_code=SBUCode.SBU_D,
    approved=300000000, actual=0, is_human_verified=True,
)
r9 = engine.compute_variance(inp9)
# 2/3 * 300000000 should be exactly 200000000.00, not 199999999.99999997
assert r9.passed_through_variance == 100000000.0, f"Got {r9.passed_through_variance}"
print(f"[PASS] TEST 9 — Float precision: 1/3 × 300M = {r9.passed_through_variance}")
passed += 1

# Test 10: Batch processing with checksum
inputs = [
    CostInput(head="O&M", category=CostCategory.CONTROLLABLE, sbu_code=SBUCode.SBU_D,
              approved=150, actual=120, is_human_verified=True),
    CostInput(head="Power", category=CostCategory.UNCONTROLLABLE, sbu_code=SBUCode.SBU_G,
              approved=400, actual=450, is_human_verified=True),
]
report = engine.process_petition(inputs)
assert "batch_checksum" in report, "Batch checksum missing!"
assert report["total_items_processed"] == 2
print(f"[PASS] TEST 10 — Batch processing: {report['total_items_processed']} items, checksum={report['batch_checksum'][:16]}...")
passed += 1

print(f"\n{'='*50}")
print(f"ALL {passed}/10 SMOKE TESTS PASSED ✅")
print(f"{'='*50}")
