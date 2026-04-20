/**
 * API Configuration
 * Centralized configuration for API endpoints and settings
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_CONFIG = {
  BASE_URL: API_BASE_URL,
  
  // Authentication Endpoints
  AUTH: {
    REGISTER: `${API_BASE_URL}/api/auth/register/`,
    LOGIN: `${API_BASE_URL}/api/auth/login/`,
    LOGOUT: `${API_BASE_URL}/api/auth/logout/`,
    CURRENT_USER: `${API_BASE_URL}/api/auth/current-user/`,
  },
  
  // Recommendation Endpoints
  RECOMMENDATIONS: {
    GET_RECOMMENDATIONS: `${API_BASE_URL}/api/recommendations/get-recommendations/`,
    FILTER_COLLEGES: `${API_BASE_URL}/api/recommendations/filter-colleges/`,
    COLLEGE_DETAIL: (id) => `${API_BASE_URL}/api/recommendations/college-detail/${id}/`,
  },
  
  // College Endpoints
  COLLEGES: {
    GET_ALL: `${API_BASE_URL}/api/colleges/`,
    BY_STATE: (state) => `${API_BASE_URL}/api/colleges/state/${state}/`,
    BY_TIER: (tier) => `${API_BASE_URL}/api/colleges/tier/${tier}/`,
    STATISTICS: `${API_BASE_URL}/api/colleges/statistics/`,
  },
  
  // Request timeout (ms)
  TIMEOUT: 10000,
  
  // Default headers
  HEADERS: {
    'Content-Type': 'application/json',
  },
};

export default API_CONFIG;
