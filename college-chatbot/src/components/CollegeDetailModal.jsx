import React, { useEffect, useState } from 'react';
import { getCollegeDetail } from '../services/recommendationService';
import '../styles/CollegeDetailModal.css';

/**
 * CollegeDetailModal Component
 * Shows detailed information about a selected college
 */
export function CollegeDetailModal({ collegeId, onClose }) {
  const [college, setCollege] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getCollegeDetail(collegeId);
        if (result.status === 'success') {
          setCollege(result.college);
        } else {
          setError(result.message || 'Failed to load college details');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [collegeId]);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Close on background click
  const handleBackgroundClick = (e) => {
    if (e.target.className === 'modal-overlay') {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleBackgroundClick}>
      <div className="modal-content">
        {/* Close Button */}
        <button className="modal-close" onClick={onClose} title="Close (Esc)">
          ✕
        </button>

        {loading && (
          <div className="modal-loading">
            <div className="loading-spinner"></div>
            <p>Loading college details...</p>
          </div>
        )}

        {error && (
          <div className="modal-error">
            <p>Error: {error}</p>
            <button className="btn btn-primary" onClick={onClose}>
              Close
            </button>
          </div>
        )}

        {college && !loading && (
          <>
            {/* Header */}
            <div className="modal-header">
              <h2>{college.name}</h2>
              <p className="college-meta">
                📍 {college.city}, {college.state}
              </p>
            </div>

            {/* Body */}
            <div className="modal-body">
              {/* Contact & Links */}
              <section className="detail-section">
                <h3>Contact & Links</h3>
                {college.website && (
                  <a
                    href={college.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="detail-link"
                  >
                    🌐 Official Website
                  </a>
                )}
                {college.collegedunia_url && (
                  <a
                    href={college.collegedunia_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="detail-link"
                  >
                    ℹ️ CollegeDunia Profile
                  </a>
                )}
              </section>

              {/* College Info */}
              <section className="detail-section">
                <h3>College Information</h3>
                <div className="info-grid">
                  <div className="info-item">
                    <span className="info-label">Degree Level:</span>
                    <span className="info-value">{college.degree_level}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Location:</span>
                    <span className="info-value">
                      {college.latitude}, {college.longitude}
                    </span>
                  </div>
                </div>
              </section>

              {/* Courses */}
              <section className="detail-section">
                <h3>Courses Offered ({college.total_courses})</h3>
                
                {college.courses && college.courses.length > 0 ? (
                  <div className="courses-list">
                    {college.courses.map((course) => (
                      <div key={course.id} className="course-item">
                        <div className="course-header">
                          <h4>{course.name}</h4>
                          <span className="stream-badge">{course.stream}</span>
                        </div>
                        <div className="course-details">
                          <div className="detail-inline">
                            <span className="detail-label">Degree:</span>
                            <span className="detail-value">{course.degree_type}</span>
                          </div>
                          <div className="detail-inline">
                            <span className="detail-label">Fees:</span>
                            <span className="detail-value">₹{course.fees_lakhs}L/year</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-data">No courses information available</p>
                )}
              </section>

              {/* Stats */}
              <section className="detail-section">
                <h3>Statistics</h3>
                <div className="stats-grid">
                  <div className="stat-box">
                    <div className="stat-number">{college.total_courses}</div>
                    <div className="stat-label">Total Courses</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-number">
                      {college.courses ? 
                        Math.round(
                          college.courses.reduce((sum, c) => sum + c.fees_lakhs, 0) / 
                          college.courses.length
                        ) : 0
                      }
                    </div>
                    <div className="stat-label">Avg. Fees (L)</div>
                  </div>
                </div>
              </section>
            </div>

            {/* Footer */}
            <div className="modal-footer">
              {college.website && (
                <a
                  href={college.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                >
                  Visit College Website
                </a>
              )}
              <button className="btn btn-secondary" onClick={onClose}>
                Close
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default CollegeDetailModal;
