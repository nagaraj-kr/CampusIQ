/**
 * Validation Utilities
 * Common validation functions for user input
 */

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid email
 */
export function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate cutoff marks
 * @param {number} cutoff - Cutoff score
 * @returns {boolean} True if valid
 */
export function isValidCutoff(cutoff) {
  const num = parseFloat(cutoff);
  return !isNaN(num) && num >= 0 && num <= 200;
}

/**
 * Validate budget amount
 * @param {number} budget - Budget amount
 * @returns {boolean} True if valid
 */
export function isValidBudget(budget) {
  const num = parseInt(budget);
  return !isNaN(num) && num > 0 && num <= 10000000;
}

/**
 * Validate course name
 * @param {string} course - Course name
 * @returns {boolean} True if valid
 */
export function isValidCourse(course) {
  return course && course.trim().length > 1;
}

/**
 * Validate location
 * @param {string} location - Location name
 * @returns {boolean} True if valid
 */
export function isValidLocation(location) {
  return location && location.trim().length > 1;
}

/**
 * Validate password strength
 * @param {string} password - Password to check
 * @returns {object} { isValid, strength, message }
 */
export function validatePassword(password) {
  let strength = 0;
  let message = '';

  if (password.length >= 8) strength++;
  if (/[a-z]/.test(password)) strength++;
  if (/[A-Z]/.test(password)) strength++;
  if (/\d/.test(password)) strength++;
  if (/[@$!%*?&]/.test(password)) strength++;

  if (strength < 2) {
    message = 'Password too weak. Use at least 8 characters with mixed case and numbers.';
  } else if (strength < 4) {
    message = 'Password is moderate strength.';
  } else {
    message = 'Password is strong.';
  }

  return {
    isValid: strength >= 2,
    strength,
    message,
  };
}

export default {
  isValidEmail,
  isValidCutoff,
  isValidBudget,
  isValidCourse,
  isValidLocation,
  validatePassword,
};
