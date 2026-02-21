import fs from 'fs';
import path from 'path';
import yaml from 'yaml';
import { GainLossSharingEngine, RegulatoryConfig, CostInput } from './GainLossSharingModule';

// Function to load the YAML configuration
function loadConfig(): RegulatoryConfig {
    const configPath = path.resolve(__dirname, '../config/regulatory_config.yaml');
    const fileContents = fs.readFileSync(configPath, 'utf8');
    // Using the yaml library to parse the external config
    return yaml.parse(fileContents);
}

// Function to run the demo simulation
function runSimulation() {
    console.log("Loading Phase 1 Deterministic Configuration...");
    const config = loadConfig();
    console.log("Configuration Loaded successfully.");

    // Initialize the engine core
    const engine = new GainLossSharingEngine(config);

    // Provide Sample Data for the demo
    // We simulate 3 distinct scenarios hitting all the core logics of the Order 30.06.2025
    const simulationData: CostInput[] = [
        {
            head: 'O&M',
            category: 'Controllable',
            approved: 180000000,
            actual: 150000000,
            // Variance: +30,000,000 (Gain)
            // Expectation: Shared 2/3 Utility, 1/3 Consumer
        },
        {
            head: 'O&M',
            category: 'Controllable',
            approved: 150000000,
            actual: 180000000,
            // Variance: -30,000,000 (Loss)
            // Expectation: Fully disallowed (100% loss borne by Utility)
            anomaly_score: 0.85 // Simulating an AI flag from Phase 2 Hook
        },
        {
            head: 'Power_Purchase',
            category: 'Uncontrollable',
            approved: 400000000,
            actual: 450000000,
            // Variance: -50,000,000 (Loss)
            // Expectation: 100% passed through to consumer
        }
    ];

    console.log("\n==============================================");
    console.log("Starting Phase 1 Processing via Engine Module");
    console.log("==============================================\n");

    simulationData.forEach((data, index) => {
        console.log(`--- Processing Scenario ${index + 1}: ${data.head} [${data.category}] ---`);
        const auditTrace = engine.processVariance(data);
        console.log(JSON.stringify(auditTrace, null, 2));
        console.log("\n");
    });
}

// Execute demo
runSimulation();
