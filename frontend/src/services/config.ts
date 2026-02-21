/**
 * API Configuration
 * Environment-specific settings for backend connectivity
 */

// API Base URL - configurable per environment
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
