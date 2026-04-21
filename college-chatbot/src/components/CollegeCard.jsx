import React from 'react';
import '../styles/CollegeCard.css';

/**
 * CollegeCard Component
 * Displays college information in a beautiful card format
 */
export function CollegeCard({ college, onViewDetails }) {
  const scoreColor = college.score >= 80 ? '#4CAF50' : college.score >= 60 ? '#FF9800' : '#f44336';
  const distanceLabel = college.distance_km ? `${college.distance_km} km away` : 'Distance N/A';

  return (
    <div className="college-card">
      {/* College Image/Placeholder */}
      <div className="college-image-container">
        <div className="college-image-placeholder">
          <div className="college-initials">
            {college.college_name
              .split(' ')
              .map(word => word[0])
              .join('')
              .substring(0, 3)
              .toUpperCase()}
          </div>
          <div className="college-name-in-image">{college.college_name}</div>
        </div>
      </div>

      {/* Score Badge */}
      <div className="score-badge" style={{ backgroundColor: scoreColor }}>
        <div className="score-number">{college.score}</div>
        <div className="score-label">match %</div>
      </div>

      {/* College Header */}
      <div className="college-header">
        <div className="header-top">
          <h3 className="college-name">{college.college_name}</h3>
          <div className="score-display">{college.score}%</div>
        </div>
        <p className="college-location">
          📍 {college.city}, {college.state}
        </p>
      </div>

      {/* Course Info */}
      <div className="course-info">
        <div className="info-row">
          <span className="label">📚 Course:</span>
          <span className="value">{college.degree_type} - {college.course_name}</span>
        </div>

        <div className="info-row">
          <span className="label">💰 Fees:</span>
          <span className="value">₹{college.fees_per_year_lakhs}L/year</span>
        </div>

        <div className="info-row">
          <span className="label">🚗 Distance:</span>
          <span className="value">{distanceLabel}</span>
        </div>
      </div>

      {/* Reasons */}
      {college.reasons && (
        <div className="reasons-section">
          <div className="reasons-pros">
            {college.reasons.pros.slice(0, 2).map((pro, idx) => (
              <div key={idx} className="reason-item pro">
                <span className="reason-icon">✓</span>
                <span className="reason-text">{pro}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {college.website && (
        <div className="card-actions">
          <a
            href={college.website}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
          >
            Visit Website
          </a>
        </div>
      )}
    </div>
  );
}

export default CollegeCard;
