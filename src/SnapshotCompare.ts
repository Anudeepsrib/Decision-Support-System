/**
 * SnapshotCompare.ts
 * Multi-User Versioning: Allows regulatory officers to create and compare
 * "Scenario A" (Base Case) vs "Scenario B" (Aggressive Disallowance) snapshots.
 * Generates a structured delta report showing the impact on the final Revenue Gap.
 */

import { AuditObject } from './AuditTrail';
import { GainLossSharingEngine, RegulatoryConfig, CostInput } from './GainLossSharingModule';

export interface Snapshot {
    id: string;
    label: string;
    created_at: string;
    created_by: string;
    inputs: CostInput[];
    results: AuditObject[];
    total_revenue_gap: number;
}

export interface DeltaReport {
    timestamp: string;
    scenario_a: { id: string; label: string; revenue_gap: number };
    scenario_b: { id: string; label: string; revenue_gap: number };
    delta: number;
    impact_direction: 'FAVORABLE' | 'ADVERSE' | 'NEUTRAL';
    line_items: DeltaLineItem[];
}

export interface DeltaLineItem {
    cost_head: string;
    scenario_a_variance: number;
    scenario_b_variance: number;
    delta: number;
}

export class SnapshotEngine {
    private engine: GainLossSharingEngine;
    private snapshots: Map<string, Snapshot> = new Map();

    constructor(config: RegulatoryConfig) {
        this.engine = new GainLossSharingEngine(config);
    }

    /**
     * Creates and stores a named snapshot from a set of cost inputs.
     */
    public createSnapshot(id: string, label: string, createdBy: string, inputs: CostInput[]): Snapshot {
        const results = inputs.map(input => this.engine.processVariance(input));
        const totalGap = results.reduce((sum, r) => sum + r.variance_amount, 0);

        const snapshot: Snapshot = {
            id,
            label,
            created_at: new Date().toISOString(),
            created_by: createdBy,
            inputs,
            results,
            total_revenue_gap: totalGap
        };

        this.snapshots.set(id, snapshot);
        return snapshot;
    }

    /**
     * Generates a Delta Report comparing two snapshots.
     */
    public compare(scenarioAId: string, scenarioBId: string): DeltaReport {
        const a = this.snapshots.get(scenarioAId);
        const b = this.snapshots.get(scenarioBId);

        if (!a || !b) {
            throw new Error(`Snapshot not found. Available: ${[...this.snapshots.keys()].join(', ')}`);
        }

        const lineItems: DeltaLineItem[] = [];
        const maxLen = Math.max(a.results.length, b.results.length);

        for (let i = 0; i < maxLen; i++) {
            const aResult = a.results[i];
            const bResult = b.results[i];
            lineItems.push({
                cost_head: aResult?.cost_head || bResult?.cost_head || 'Unknown',
                scenario_a_variance: aResult?.variance_amount ?? 0,
                scenario_b_variance: bResult?.variance_amount ?? 0,
                delta: (bResult?.variance_amount ?? 0) - (aResult?.variance_amount ?? 0)
            });
        }

        const delta = b.total_revenue_gap - a.total_revenue_gap;

        return {
            timestamp: new Date().toISOString(),
            scenario_a: { id: a.id, label: a.label, revenue_gap: a.total_revenue_gap },
            scenario_b: { id: b.id, label: b.label, revenue_gap: b.total_revenue_gap },
            delta,
            impact_direction: delta > 0 ? 'FAVORABLE' : delta < 0 ? 'ADVERSE' : 'NEUTRAL',
            line_items: lineItems
        };
    }
}

// --- Demo Execution ---
if (require.main === module) {
    const config: RegulatoryConfig = {
        escalation_indices: { cpi_weight: 0.70, wpi_weight: 0.30 },
        sharing_mechanism: {
            controllable_gains: { utility_share: 2 / 3, consumer_share: 1 / 3 },
            controllable_losses: { utility_share: 1.0, consumer_share: 0.0 },
            uncontrollable_variances: { utility_share: 0.0, consumer_share: 1.0 }
        },
        technical_loss_targets: { sbu_distribution: 0.14 }
    };

    const snapshotEngine = new SnapshotEngine(config);

    // Scenario A: Base Case
    snapshotEngine.createSnapshot('base_case', 'Base Case (Conservative)', 'Officer_A', [
        { head: 'O&M', category: 'Controllable', approved: 150, actual: 140 },
        { head: 'Power_Purchase', category: 'Uncontrollable', approved: 400, actual: 420 }
    ]);

    // Scenario B: Aggressive Disallowance
    snapshotEngine.createSnapshot('aggressive', 'Aggressive Disallowance', 'Officer_A', [
        { head: 'O&M', category: 'Controllable', approved: 150, actual: 180 },
        { head: 'Power_Purchase', category: 'Uncontrollable', approved: 400, actual: 420 }
    ]);

    const deltaReport = snapshotEngine.compare('base_case', 'aggressive');

    console.log("\n--- Snapshot Delta Report ---");
    console.log(JSON.stringify(deltaReport, null, 2));
}
