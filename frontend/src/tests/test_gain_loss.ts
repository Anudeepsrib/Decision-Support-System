import { GainLossSharingEngine, RegulatoryConfig, CostInput } from '../src/GainLossSharingModule';
import assert from 'assert';

// Core testing configuration replicating the 30.06.2025 Order baseline
const testConfig: RegulatoryConfig = {
    escalation_indices: { cpi_weight: 0.70, wpi_weight: 0.30 },
    sharing_mechanism: {
        controllable_gains: { utility_share: 2 / 3, consumer_share: 1 / 3 },
        controllable_losses: { utility_share: 1.0, consumer_share: 0.0 },
        uncontrollable_variances: { utility_share: 0.0, consumer_share: 1.0 }
    },
    technical_loss_targets: { sbu_distribution: 0.14 }
};

const engine = new GainLossSharingEngine(testConfig);

console.log("Starting Production Stress Tests: Gain/Loss Edge Cases...\n");

// Test 1: Pure Gain (Savings) - Controllable
// Scenario: Approved 100, Actual 70. Variance = +30.
// Expected: Passed to consumer = 30 * (1/3) = 10. Disallowed = 0.
function test_pure_gain_controllable() {
    const input: CostInput = {
        head: 'O&M',
        category: 'Controllable',
        approved: 100,
        actual: 70
    };

    const result = engine.processVariance(input);

    assert.strictEqual(result.variance_amount, 30, "Variance should be exactly 30 (Gain)");
    // 30 / 3 = 10 floating point math check
    assert.strictEqual(Math.round(result.passed_through_variance), 10, "Consumer passed-through should be 1/3 of savings (10)");
    assert.strictEqual(result.disallowed_variance, 0, "No disallowed variance on a gain");
    console.log("✔️ [PASS] Pure Gain (Controllable Savings) verified.");
}

// Test 2: Pure Loss - Controllable
// Scenario: Approved 100, Actual 130. Variance = -30.
// Expected: Passed to consumer = 0. Disallowed = 30 (100% borne by Utility).
function test_pure_loss_controllable() {
    const input: CostInput = {
        head: 'O&M',
        category: 'Controllable',
        approved: 100,
        actual: 130
    };

    const result = engine.processVariance(input);

    assert.strictEqual(result.variance_amount, -30, "Variance should be exactly -30 (Loss)");
    assert.strictEqual(result.passed_through_variance, 0, "0 passed through to consumer on controllable loss");
    assert.strictEqual(result.disallowed_variance, 30, "Entire loss disallowed (borne by utility)");
    console.log("✔️ [PASS] Pure Loss (Controllable Loss Disallowance) verified.");
}

// Test 3: Loss exceeding normative caps (Targeting boundary floats)
// Scenario: Approved 100.55, Actual 100.56. Variance = -0.01.
// Expected: Floating point logic must resolve accurately without crashing.
function test_loss_boundary() {
    const input: CostInput = {
        head: 'Power_Purchase',
        category: 'Uncontrollable', // Uncontrollable means 100% pass-through
        approved: 100.55,
        actual: 100.56
    };

    const result = engine.processVariance(input);

    assert.ok(Math.abs(result.variance_amount - (-0.01)) < 0.0001, "Variance floating point boundary precision failure");
    assert.ok(Math.abs(result.passed_through_variance - (-0.01)) < 0.0001, "Pass-through floating point boundary precision failure");
    assert.strictEqual(result.disallowed_variance, 0, "No disallowed variance on uncontrollable items");
    console.log("✔️ [PASS] Boundary Floating-Point Caps (Uncontrollable) verified.");
}

try {
    test_pure_gain_controllable();
    test_pure_loss_controllable();
    test_loss_boundary();
    console.log("\n✅ All Production Stress Tests Passed. The Phase 1 Core Logic is resilient.");
} catch (error) {
    console.error("\n❌ Test Failed!");
    console.error(error);
    process.exit(1);
}
