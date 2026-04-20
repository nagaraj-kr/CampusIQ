/**
 * Constants
 * Application-wide constants and configuration values
 */

export const COLLEGE_TIERS = [
  'IIT',
  'NIT',
  'IIIT',
  'Govt College',
  'Autonomous',
  'Tier-1 Premium',
  'Tier-2 Professional',
  'Tier-3 Regional',
];

export const COLLEGE_TYPES = [
  'Government',
  'Private',
  'Autonomous',
];

export const COURSES = [
  'B.Tech CSE',
  'B.Tech Mechanical',
  'B.Tech Electrical',
  'B.Tech Civil',
  'B.Tech Electronics',
  'MBA',
  'M.Tech',
  'BCA',
];

export const STATES = [
  'Tamil Nadu',
  'Andhra Pradesh',
  'Telangana',
  'Karnataka',
  'Maharashtra',
  'Delhi',
  'West Bengal',
  'Gujarat',
  'Rajasthan',
  'Punjab',
  'Uttar Pradesh',
  'Other',
];

export const BUDGET_RANGES = [
  { label: 'Below ₹2 Lakh', value: 200000 },
  { label: '₹2 - ₹5 Lakh', value: 500000 },
  { label: '₹5 - ₹10 Lakh', value: 1000000 },
  { label: 'Above ₹10 Lakh', value: 10000000 },
];

export const CUTOFF_EXAMPLES = [
  'HSC Cutoff (out of 200)',
  'TNEA Cutoff',
  'JEE Mains Score',
  'NEET Score',
];

export const MATCH_SCORE_LABELS = {
  90: 'Excellent Match',
  75: 'Very Good',
  60: 'Good',
  45: 'Moderate',
  30: 'Fair',
  0: 'Poor Match',
};

export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  AUTH_ERROR: 'Authentication failed. Please try again.',
  VALIDATION_ERROR: 'Please fill all required fields correctly.',
  SERVER_ERROR: 'Server error. Please try again later.',
};

export const SUCCESS_MESSAGES = {
  LOGIN_SUCCESS: 'Login successful!',
  LOGOUT_SUCCESS: 'Logged out successfully.',
  REGISTRATION_SUCCESS: 'Registration successful! Please log in.',
};

export default {
  COLLEGE_TIERS,
  COLLEGE_TYPES,
  COURSES,
  STATES,
  BUDGET_RANGES,
  CUTOFF_EXAMPLES,
  MATCH_SCORE_LABELS,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
};
