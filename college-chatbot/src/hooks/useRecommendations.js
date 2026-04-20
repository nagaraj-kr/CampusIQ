/**
 * Recommendations Hook
 * Custom React hook for managing college recommendations
 */

import { useState, useCallback } from 'react';
import recommendationService from '../services/recommendationService';

export function useRecommendations() {
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getRecommendations = useCallback(async (preferences) => {
    setLoading(true);
    setError(null);
    try {
      const response = await recommendationService.getRecommendations(preferences);
      setRecommendations(response.recommendations || []);
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const filterColleges = useCallback(async (filters) => {
    setLoading(true);
    setError(null);
    try {
      const response = await recommendationService.filterColleges(filters);
      setRecommendations(response.colleges || []);
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getCollegeDetail = useCallback(async (collegeId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await recommendationService.getCollegeDetail(collegeId);
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearRecommendations = useCallback(() => {
    setRecommendations(null);
    setError(null);
  }, []);

  return {
    recommendations,
    loading,
    error,
    getRecommendations,
    filterColleges,
    getCollegeDetail,
    clearRecommendations,
  };
}

export default useRecommendations;
