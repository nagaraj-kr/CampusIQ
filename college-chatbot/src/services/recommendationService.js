/**
 * Recommendation Service
 * Handles all recommendation-related API calls
 */

import { API_CONFIG } from '../config/api.config';
import { getCsrfToken } from '../utils/csrf';

/**
 * Get college recommendations based on student profile
 * @param {Object} preferences - Student preferences (cutoff, budget, course, location, etc)
 * @returns {Promise} Array of recommended colleges with scores
 */
export async function getRecommendations(preferences) {
  try {
    const response = await fetch(API_CONFIG.RECOMMENDATIONS.GET_RECOMMENDATIONS, {
      method: 'POST',
      headers: {
        ...API_CONFIG.HEADERS,
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(preferences),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to get recommendations');
    }

    return await response.json();
  } catch (error) {
    console.error('Recommendation error:', error);
    throw error;
  }
}

/**
 * Filter colleges by various criteria
 * @param {Object} filters - Filter criteria (state, tier, type, etc)
 * @returns {Promise} Filtered list of colleges
 */
export async function filterColleges(filters) {
  try {
    // Build query string from filters
    const queryParams = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) queryParams.append(key, value);
    });

    const url = `${API_CONFIG.RECOMMENDATIONS.FILTER_COLLEGES}?${queryParams}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: API_CONFIG.HEADERS,
    });

    if (!response.ok) {
      throw new Error('Failed to filter colleges');
    }

    return await response.json();
  } catch (error) {
    console.error('Filter error:', error);
    throw error;
  }
}

/**
 * Get detailed information about a specific college
 * @param {number} collegeId - ID of the college
 * @returns {Promise} Detailed college information
 */
export async function getCollegeDetail(collegeId) {
  try {
    const response = await fetch(API_CONFIG.RECOMMENDATIONS.COLLEGE_DETAIL(collegeId), {
      method: 'GET',
      headers: API_CONFIG.HEADERS,
    });

    if (!response.ok) {
      throw new Error('Failed to fetch college details');
    }

    return await response.json();
  } catch (error) {
    console.error('College detail error:', error);
    throw error;
  }
}

export default {
  getRecommendations,
  filterColleges,
  getCollegeDetail,
};
