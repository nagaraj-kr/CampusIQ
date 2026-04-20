const BASE_URL = import.meta.env.VITE_API_URL || '';

// Helper function to get CSRF token from cookies
function getCsrfToken() {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
          }
      }
  }
  return cookieValue;
}

// ==================== AUTHENTICATION API ====================

export async function registerUser(userData) {
  const endpoint = BASE_URL 
    ? `${BASE_URL}/api/auth/register/`
    : '/api/auth/register/';
  
  const headers = { 'Content-Type': 'application/json' };
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  
  const res = await fetch(endpoint, {
    method: 'POST',
    headers,
    credentials: 'include', // Enable session cookies
    body: JSON.stringify({
      email: userData.email,
      first_name: userData.first_name,
      last_name: userData.last_name,
      password: userData.password,
      password2: userData.password2,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.errors ? Object.values(err.errors)[0]?.[0] || 'Registration failed' : err.message);
  }

  return res.json();
}

export async function loginUser(credentials) {
  const endpoint = BASE_URL 
    ? `${BASE_URL}/api/auth/login/`
    : '/api/auth/login/';
  
  const headers = { 'Content-Type': 'application/json' };
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  
  const res = await fetch(endpoint, {
    method: 'POST',
    headers,
    credentials: 'include', // Enable session cookies
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    // Better error extraction
    if (err.errors) {
      const errMessages = Object.values(err.errors).flat();
      throw new Error(errMessages[0] || 'Login failed');
    }
    throw new Error(err.detail || err.message || 'Login failed');
  }

  return res.json();
}

export async function logoutUser() {
  const endpoint = BASE_URL 
    ? `${BASE_URL}/api/auth/logout/`
    : '/api/auth/logout/';
  
  const headers = { 'Content-Type': 'application/json' };
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  
  const res = await fetch(endpoint, {
    method: 'POST',
    headers,
    credentials: 'include',
  });

  if (!res.ok) {
    throw new Error('Logout failed');
  }

  return res.json();
}

export async function getCurrentUser() {
  const endpoint = BASE_URL 
    ? `${BASE_URL}/api/auth/current-user/`
    : '/api/auth/current-user/';
  
  const res = await fetch(endpoint, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });

  if (res.status === 401) {
    return null; // Not authenticated
  }

  if (!res.ok) {
    throw new Error('Failed to fetch current user');
  }

  return res.json();
}

export async function updateUserProfile(profileData) {
  const endpoint = BASE_URL 
    ? `${BASE_URL}/api/profile/`
    : '/api/profile/';
  
  const headers = { 'Content-Type': 'application/json' };
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  
  const res = await fetch(endpoint, {
    method: 'PUT',
    headers,
    credentials: 'include',
    body: JSON.stringify(profileData),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.errors ? Object.values(err.errors)[0]?.[0] || 'Update failed' : err.detail);
  }

  return res.json();
}

// ==================== VALIDATION UTILITIES ====================

export function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!re.test(email)) {
    return 'Invalid email format';
  }
  if (email.length > 254) {
    return 'Email is too long';
  }
  return null;
}

export function validatePassword(password) {
  if (password.length < 6) {
    return 'Password must be at least 6 characters';
  }
  if (password.length > 128) {
    return 'Password is too long';
  }
  if (!/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
    return 'Password must contain uppercase letter and number';
  }
  return null;
}

export function validateUsername(username) {
  if (username.length < 3) {
    return 'Username must be at least 3 characters';
  }
  if (username.length > 150) {
    return 'Username is too long';
  }
  if (!/^[a-zA-Z0-9_@.-]+$/.test(username)) {
    return 'Username can only contain letters, numbers, and @._- characters';
  }
  return null;
}

export function validateName(name) {
  if (name.trim().length < 2) {
    return 'Name must be at least 2 characters';
  }
  if (name.length > 150) {
    return 'Name is too long';
  }
  if (!/^[a-zA-Z\s'-]+$/.test(name)) {
    return 'Name can only contain letters, spaces, hyphens, and apostrophes';
  }
  return null;
}

// ==================== COLLEGE RECOMMENDATIONS ====================
export async function fetchRecommendations(studentData) {
  const payload = {
    cutoff_marks: studentData.cutoff || 0,
    budget: studentData.budget || 1000000,
    course_type: studentData.course || 'CSE',
    latitude: studentData.latitude || 13.0827,   // default: Chennai
    longitude: studentData.longitude || 80.2707,
    location: studentData.location || 'Tamil Nadu',
    max_distance: 1000,
    limit: 10
  };

  // Handle both development proxy and production API paths
  const endpoint = BASE_URL 
    ? `${BASE_URL}/api/get-recommendations/`
    : '/api/get-recommendations/';

  const headers = { 'Content-Type': 'application/json' };
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }

  const res = await fetch(endpoint, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `Server error: ${res.status}`);
  }

  return res.json();
}

// City → lat/lng lookup (common TN cities)
const CITY_COORDS = {
  chennai:     { lat: 13.0827, lng: 80.2707 },
  coimbatore:  { lat: 11.0168, lng: 76.9558 },
  madurai:     { lat:  9.9252, lng: 78.1198 },
  trichy:      { lat: 10.7905, lng: 78.7047 },
  tiruchirappalli: { lat: 10.7905, lng: 78.7047 },
  salem:       { lat: 11.6643, lng: 78.1460 },
  tirunelveli: { lat:  8.7139, lng: 77.7567 },
  vellore:     { lat: 12.9165, lng: 79.1325 },
  erode:       { lat: 11.3410, lng: 77.7172 },
  thanjavur:   { lat: 10.7870, lng: 79.1378 },
  thoothukudi: { lat:  8.7642, lng: 78.1348 },
  dindigul:    { lat: 10.3624, lng: 77.9695 },
  kanyakumari: { lat:  8.0883, lng: 77.5385 },
  bangalore:   { lat: 12.9716, lng: 77.5946 },
  bengaluru:   { lat: 12.9716, lng: 77.5946 },
};

export function resolveCoords(cityName) {
  const key = cityName.toLowerCase().trim();
  return CITY_COORDS[key] || CITY_COORDS['chennai'];
}
