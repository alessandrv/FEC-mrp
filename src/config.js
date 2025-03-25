/**
 * Application configuration
 * Centralizes access to environment variables with fallback values
 */

// API endpoints
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://172.16.16.66:8000';
const WEBSOCKET_URL = process.env.REACT_APP_WEBSOCKET_URL || 'ws://172.16.16.66:8000';

// Export configuration constants
export { 
  API_BASE_URL,
  WEBSOCKET_URL
}; 