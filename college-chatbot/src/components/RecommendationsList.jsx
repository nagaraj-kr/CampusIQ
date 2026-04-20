import React, { useState } from 'react';
import CollegeCard from './CollegeCard';
import CollegeDetailModal from './CollegeDetailModal';
import '../styles/RecommendationsList.css';

/**
 * RecommendationsList Component
 * Displays a list of recommended colleges in card format
 */
export function RecommendationsList({ 
  recommendations, 
  loading, 
  error,
  onRefresh 
}) {
  const [selectedCollege, setSelectedCollege] = useState(null);
  const [sortBy, setSortBy] = useState('score');

  if (error) {
    return (
      <div className="recommendations-error">
        <div className="error-icon">⚠️</div>
        <h3>Error Loading Recommendations</h3>
        <p>{error}</p>
        <button className="btn btn-primary" onClick={onRefresh}>
          Try Again
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="recommendations-loading">
        <div className="loading-spinner"></div>
        <p>Finding best colleges for you...</p>
      </div>
    );
  }

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="recommendations-empty">
        <div className="empty-icon">🎓</div>
        <h3>No Recommendations Yet</h3>
        <p>Enter your preferences to get started</p>
      </div>
    );
  }

  // Sort recommendations
  const sortedRecommendations = [...recommendations].sort((a, b) => {
    switch (sortBy) {
      case 'score':
        return b.score - a.score;
      case 'fees':
        return a.fees_per_year_lakhs - b.fees_per_year_lakhs;
      case 'distance':
        return (a.distance_km || Infinity) - (b.distance_km || Infinity);
      default:
        return 0;
    }
  });

  return (
    <div className="recommendations-container">
      {/* Header */}
      <div className="recommendations-header">
        <div className="header-left">
          <h2>Recommended Colleges</h2>
          <p className="results-count">
            {recommendations.length} college{recommendations.length !== 1 ? 's' : ''} found
          </p>
        </div>

        {/* Sort Controls */}
        <div className="sort-controls">
          <label htmlFor="sort-select">Sort by:</label>
          <select
            id="sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="sort-select"
          >
            <option value="score">Best Match</option>
            <option value="fees">Lowest Fees</option>
            <option value="distance">Closest Location</option>
          </select>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="recommendations-stats">
        <div className="stat-item">
          <span className="stat-label">Average Match:</span>
          <span className="stat-value">
            {(recommendations.reduce((sum, r) => sum + r.score, 0) / recommendations.length).toFixed(0)}%
          </span>
        </div>

        <div className="stat-item">
          <span className="stat-label">Budget Range:</span>
          <span className="stat-value">
            ₹{Math.min(...recommendations.map(r => r.fees_per_year_lakhs)).toFixed(1)}L - ₹{Math.max(...recommendations.map(r => r.fees_per_year_lakhs)).toFixed(1)}L
          </span>
        </div>

        <div className="stat-item">
          <span className="stat-label">Distance:</span>
          <span className="stat-value">
            {recommendations.some(r => r.distance_km) 
              ? `Up to ${Math.max(...recommendations.filter(r => r.distance_km).map(r => r.distance_km)).toFixed(0)} km`
              : 'N/A'
            }
          </span>
        </div>
      </div>

      {/* College Cards List */}
      <div className="colleges-grid">
        {sortedRecommendations.map((college, index) => (
          <div key={college.college_id || index} className="college-item">
            <div className="item-number">{index + 1}</div>
            <CollegeCard
              college={college}
              onViewDetails={(collegeId) => setSelectedCollege(collegeId)}
            />
          </div>
        ))}
      </div>

      {/* Detail Modal */}
      {selectedCollege && (
        <CollegeDetailModal
          collegeId={selectedCollege}
          onClose={() => setSelectedCollege(null)}
        />
      )}
    </div>
  );
}

export default RecommendationsList;
