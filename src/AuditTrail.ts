/**
 * AuditTrail.ts
 * Interfaces for generating compliance-grade JSON metadata objects.
 */

export interface RegulatoryReference {
    clause: string;
    description: string;
    order_date: string;
}

export interface AuditObject<T = any> {
    timestamp: string;
    scenario: string;
    cost_head: "O&M" | "Power_Purchase" | "Interest" | "Other";
    variance_category: "Controllable" | "Uncontrollable";
    approved_amount: number;
    actual_amount: number;
    variance_amount: number;
    disallowed_variance: number;
    passed_through_variance: number;
    logic_applied: string;
    regulatory_reference: RegulatoryReference;
    metadata: {
        engine_version: string;
        flags: string[];
        ai_hooks_active?: string[];
    };
    raw_data_snapshot?: T;
}
