/**
 * College Service
 * Handles college data retrieval and searching
 */

import { API_CONFIG } from '../config/api.config';

/**
 * Get all colleges
 * @returns {Promise} List of all colleges
 */
export async function getAllColleges() {
  try {
    const response = await fetch(API_CONFIG.COLLEGES.GET_ALL, {
      method: 'GET',
      headers: API_CONFIG.HEADERS,
    });

    if (!response.ok) {
      throw new Error('Failed to fetch colleges');
    }

    return await response.json();
  } catch (error) {
    console.error('Get colleges error:', error);
    throw error;
  }
}

/**
 * Get colleges by state
 * @param {string} state - State name
 * @returns {Promise} Colleges in the specified state
 */
export async function getCollegesByState(state) {
  try {
    const response = await fetch(API_CONFIG.COLLEGES.BY_STATE(state), {
      method: 'GET',
      headers: API_CONFIG.HEADERS,
    });

    if (!response.ok) {
      throw new Error('Failed to fetch colleges by state');
    }

    return await response.json();
  } catch (error) {
    console.error('Get colleges by state error:', error);
    throw error;
  }
}

/**
 * Get colleges by tier
 * @param {string} tier - College tier (IIT, NIT, IIIT, etc)
 * @returns {Promise} Colleges of the specified tier
 */
export async function getCollegesByTier(tier) {
  try {
    const response = await fetch(API_CONFIG.COLLEGES.BY_TIER(tier), {
      method: 'GET',
      headers: API_CONFIG.HEADERS,
    });

    if (!response.ok) {
      throw new Error('Failed to fetch colleges by tier');
    }

    return await response.json();
  } catch (error) {
    console.error('Get colleges by tier error:', error);
    throw error;
  }
}

/**
 * Get college statistics
 * @returns {Promise} Statistics about colleges in database
 */
export async function getCollegeStatistics() {
  try {
    const response = await fetch(API_CONFIG.COLLEGES.STATISTICS, {
      method: 'GET',
      headers: API_CONFIG.HEADERS,
    });

    if (!response.ok) {
      throw new Error('Failed to fetch college statistics');
    }

    return await response.json();
  } catch (error) {
    console.error('Get statistics error:', error);
    throw error;
  }
}

export default {
  getAllColleges,
  getCollegesByState,
  getCollegesByTier,
  getCollegeStatistics,
};
