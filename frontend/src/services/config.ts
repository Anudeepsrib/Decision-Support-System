/**
 * API Configuration
 * Environment-specific settings for backend connectivity
 * 
 * DEMO MODE: Set REACT_APP_DEMO_MODE=true for frictionless demo experience
 */

// API Base URL - configurable per environment
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Demo Mode Flag
export const IS_DEMO_MODE = process.env.REACT_APP_DEMO_MODE === 'true';

// Demo Case ID (preloaded in demo mode)
export const DEMO_CASE_ID = 'demo-case-001';

// Request timeout in milliseconds
export const REQUEST_TIMEOUT = 30000;

// Retry configuration
export const RETRY_CONFIG = {
  maxRetries: 3,
  retryDelay: 1000, // ms
  retryableStatuses: [429, 500, 502, 503, 504],
};

// WebSocket configuration (for future real-time features)
export const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
