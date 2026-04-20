/**
 * Authentication Service
 * Handles all authentication-related API calls
 */

import { API_CONFIG } from '../config/api.config';
import { getCsrfToken } from '../utils/csrf';

/**
 * Register a new user
 * @param {Object} userData - User registration data
 * @returns {Promise} Response with user and profile data
 */
export async function registerUser(userData) {
  try {
    const response = await fetch(API_CONFIG.AUTH.REGISTER, {
      method: 'POST',
      headers: {
        ...API_CONFIG.HEADERS,
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Registration failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
}

/**
 * Login user
 * @param {Object} credentials - Username and password
 * @returns {Promise} Response with user and profile data
 */
export async function loginUser(credentials) {
  try {
    const response = await fetch(API_CONFIG.AUTH.LOGIN, {
      method: 'POST',
      headers: {
        ...API_CONFIG.HEADERS,
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Login failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

/**
 * Logout current user
 * @returns {Promise} Response confirming logout
 */
export async function logoutUser() {
  try {
    const response = await fetch(API_CONFIG.AUTH.LOGOUT, {
      method: 'POST',
      headers: {
        ...API_CONFIG.HEADERS,
        'X-CSRFToken': getCsrfToken(),
      },
    });

    if (!response.ok) {
      throw new Error('Logout failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Logout error:', error);
    throw error;
  }
}

/**
 * Get current authenticated user
 * @returns {Promise} Current user data
 */
export async function getCurrentUser() {
  try {
    const response = await fetch(API_CONFIG.AUTH.CURRENT_USER, {
      method: 'GET',
      headers: API_CONFIG.HEADERS,
    });

    if (!response.ok) {
      throw new Error('Failed to fetch current user');
    }

    return await response.json();
  } catch (error) {
    console.error('Current user error:', error);
    throw error;
  }
}

export default {
  registerUser,
  loginUser,
  logoutUser,
  getCurrentUser,
};
