/**
 * GainLossSharingModule.ts
 * Core logic for evaluating Controllable/Uncontrollable cost variances.
 * Designed with "Modular Integration Hooks" for Phase 2 AI ingestion.
 */

import { AuditObject, RegulatoryReference } from "./AuditTrail";

// Types simulating the Data Layer
export interface CostInput {
    head: "O&M" | "Power_Purchase" | "Interest" | "Other";
    category: "Controllable" | "Uncontrollable";
    approved: number;
    actual: number;
    // Phase 2 AI Hook Reservation
    anomaly_score?: number;
}

export interface SharingConfig {
    utility_share: number;
    consumer_share: number;
}

export interface RegulatoryConfig {
    escalation_indices: { cpi_weight: number; wpi_weight: number };
    sharing_mechanism: {
        controllable_gains: SharingConfig;
        controllable_losses: SharingConfig;
        uncontrollable_variances: SharingConfig;
    };
    technical_loss_targets: { sbu_distribution: number };
}

export class GainLossSharingEngine {
    private config: RegulatoryConfig;

    constructor(config: RegulatoryConfig) {
        this.config = config;
    }

    /**
     * Compute variance and apply sharing principles based on the 30.06.2025 Order.
     * @param input Data ingested from PostgreSQL or Phase 2 NLP Parsers.
     * @returns AuditObject ready for JSON serialization
     */
    public processVariance(input: CostInput): AuditObject {
        const variance = input.approved - input.actual; // positive means gain (savings), negative means loss
        const isGain = variance >= 0;

        let utilityShareRatio = 0;
        let consumerShareRatio = 0;
        let logicStr = "";

        if (input.category === "Controllable") {
            if (isGain) {
                utilityShareRatio = this.config.sharing_mechanism.controllable_gains.utility_share;
                consumerShareRatio = this.config.sharing_mechanism.controllable_gains.consumer_share;
                logicStr = "Controllable Gain (Savings) split 2/3 Utility, 1/3 Consumer.";
            } else {
                utilityShareRatio = this.config.sharing_mechanism.controllable_losses.utility_share;
                consumerShareRatio = this.config.sharing_mechanism.controllable_losses.consumer_share;
                logicStr = "Controllable Loss fully borne by Utility (Disallowed).";
            }
        } else {
            // Uncontrollable
            utilityShareRatio = this.config.sharing_mechanism.uncontrollable_variances.utility_share;
            consumerShareRatio = this.config.sharing_mechanism.uncontrollable_variances.consumer_share;
            logicStr = "Uncontrollable Variance fully passed through to Consumer.";
        }

        const utilityImpact = Math.abs(variance) * utilityShareRatio;
        const consumerImpact = Math.abs(variance) * consumerShareRatio;

        const disallowed = (input.category === "Controllable" && !isGain) ? Math.abs(variance) : 0;
        const passedThrough = (input.category === "Uncontrollable") ? variance : (isGain ? consumerImpact : 0);

        const ref: RegulatoryReference = {
            clause: "Regulation 9.2 - Gain/Loss Sharing mechanism",
            description: input.category === "Controllable" ? "Sharing of controllable factors efficiency gains/losses" : "Pass-through of uncontrollable factors",
            order_date: "30.06.2025"
        };

        const audit: AuditObject = {
            timestamp: new Date().toISOString(),
            scenario: isGain ? `${input.head} Gain Sharing` : `${input.head} Loss Disallowance`,
            cost_head: input.head,
            variance_category: input.category,
            approved_amount: input.approved,
            actual_amount: input.actual,
            variance_amount: variance,
            disallowed_variance: disallowed,
            passed_through_variance: passedThrough,
            logic_applied: logicStr,
            regulatory_reference: ref,
            metadata: {
                engine_version: "Phase1-v1.0.0",
                flags: input.anomaly_score && input.anomaly_score > 0.8 ? ["HIGH_ANOMALY_FLAG"] : []
            }
        };

        return audit;
    }
}
