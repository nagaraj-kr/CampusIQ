import { useState } from "react";
import {
  registerUser,
  loginUser,
  validateEmail,
  validatePassword,
  validateName,
} from "../api";
import "./AuthModal.css";

export default function AuthModal({ mode, onClose, onLogin, onSwitchMode }) {
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    password2: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  const isLogin = mode === "login";

  // Validate single field
  const validateField = (name, value) => {
    let err = null;

    if (name === "email") {
      err = validateEmail(value);
    } else if (name === "password") {
      err = validatePassword(value);
    } else if ((name === "first_name" || name === "last_name") && !isLogin) {
      if (value.trim()) {
        err = validateName(value);
      }
    } else if (name === "password2" && !isLogin) {
      if (value !== form.password) {
        err = "Passwords do not match";
      }
    }

    setFieldErrors((prev) => ({
      ...prev,
      [name]: err,
    }));

    return err;
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setError("");
    validateField(name, value);
  };

  const validateForm = () => {
    const newErrors = {};

    if (isLogin) {
      // Login validation
      if (!form.email || !form.password) {
        newErrors.general = "Email and password are required";
        return newErrors;
      }

      const emailErr = validateEmail(form.email);
      if (emailErr) newErrors.email = emailErr;
    } else {
      // Signup validation
      if (!form.email || !form.password || !form.password2) {
        newErrors.general = "All fields are required";
        return newErrors;
      }
      if (!form.first_name.trim()) {
        newErrors.first_name = "First name is required";
      } else {
        const nameErr = validateName(form.first_name);
        if (nameErr) newErrors.first_name = nameErr;
      }

      const emailErr = validateEmail(form.email);
      if (emailErr) newErrors.email = emailErr;

      const passwordErr = validatePassword(form.password);
      if (passwordErr) newErrors.password = passwordErr;

      if (form.password !== form.password2) {
        newErrors.password2 = "Passwords do not match";
      }
    }

    return newErrors;
  };

  const handleSubmit = async () => {
    setError("");
    const validationErrors = validateForm();

    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setError(validationErrors.general || "Please fix the errors above");
      return;
    }

    setLoading(true);

    try {
      if (isLogin) {
        const result = await loginUser({
          email: form.email,
          password: form.password,
        });

        if (result.user) {
          onLogin({
            username: result.user.username,
            email: result.user.email,
            name: result.user.first_name || result.user.username,
          });
        }
      } else {
        const result = await registerUser({
          first_name: form.first_name,
          last_name: form.last_name || "",
          email: form.email,
          password: form.password,
          password2: form.password2,
        });

        if (result.user) {
          onLogin({
            username: result.user.username,
            email: result.user.email,
            name: result.user.first_name || result.user.username,
          });
        }
      }
    } catch (err) {
      setError(err.message || "An error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrength = (pwd) => {
    if (!pwd) return { score: 0, label: "", color: "" };
    let score = 0;
    if (pwd.length >= 6) score++;
    if (pwd.length >= 10) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[a-z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^a-zA-Z0-9]/.test(pwd)) score++;

    const labels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"];
    const colors = ["#dc2626", "#ea580c", "#eab308", "#84cc16", "#22c55e", "#16a34a"];

    return { score: Math.min(score, 5), label: labels[Math.min(score, 5)], color: colors[Math.min(score, 5)] };
  };

  const passwordStrength = getPasswordStrength(form.password);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-logo">🎓</div>
        <h2 className="modal-title">{isLogin ? "Welcome back" : "Create account"}</h2>
        <p className="modal-sub">
          {isLogin ? "Sign in to access personalized college recommendations" : "Join to unlock personalized recommendations"}
        </p>

        <div className="modal-fields">
          {!isLogin && (
            <>
              <div className="form-group">
                <input
                  className={`modal-input ${fieldErrors.first_name ? "error" : ""}`}
                  placeholder="First name"
                  name="first_name"
                  value={form.first_name}
                  onChange={handleInputChange}
                  disabled={loading}
                  autoComplete="given-name"
                />
                {fieldErrors.first_name && (
                  <span className="field-error">{fieldErrors.first_name}</span>
                )}
              </div>

              <div className="form-group">
                <input
                  className={`modal-input`}
                  placeholder="Last name (optional)"
                  name="last_name"
                  value={form.last_name}
                  onChange={handleInputChange}
                  disabled={loading}
                  autoComplete="family-name"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <input
              className={`modal-input ${fieldErrors.email ? "error" : ""}`}
              type="email"
              placeholder="Email address"
              name="email"
              value={form.email}
              onChange={handleInputChange}
              disabled={loading}
              autoComplete="email"
            />
            {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
          </div>

          <div className="form-group">
            <input
              className={`modal-input ${fieldErrors.password ? "error" : ""}`}
              type="password"
              placeholder="Password"
              name="password"
              value={form.password}
              onChange={handleInputChange}
              disabled={loading}
              autoComplete="current-password"
            />
            {fieldErrors.password && (
              <span className="field-error">{fieldErrors.password}</span>
            )}
            {!isLogin && form.password && (
              <div className="password-strength">
                <div className="strength-bar">
                  <div
                    className="strength-fill"
                    style={{
                      width: `${(passwordStrength.score / 5) * 100}%`,
                      backgroundColor: passwordStrength.color,
                    }}
                  />
                </div>
                <span
                  className="strength-label"
                  style={{ color: passwordStrength.color }}
                >
                  {passwordStrength.label}
                </span>
              </div>
            )}
          </div>

          {!isLogin && (
            <div className="form-group">
              <input
                className={`modal-input ${fieldErrors.password2 ? "error" : ""}`}
                type="password"
                placeholder="Confirm password"
                name="password2"
                value={form.password2}
                onChange={handleInputChange}
                disabled={loading}
                autoComplete="new-password"
              />
              {fieldErrors.password2 && (
                <span className="field-error">{fieldErrors.password2}</span>
              )}
            </div>
          )}
        </div>

        {error && <p className="modal-error">{error}</p>}

        <button
          className="modal-btn"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading
            ? isLogin
              ? "Signing in..."
              : "Creating account..."
            : isLogin
              ? "Sign in"
              : "Create account"}
        </button>

        <p className="modal-switch">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button
            className="modal-switch-btn"
            onClick={() => {
              onSwitchMode(isLogin ? "signup" : "login");
              setError("");
              setFieldErrors({});
            }}
            disabled={loading}
          >
            {isLogin ? "Sign up" : "Log in"}
          </button>
        </p>

        <p className="modal-privacy">
          By signing {isLogin ? "in" : "up"}, you agree to our
          <a href="#" onClick={(e) => e.preventDefault()}>
            {" "}
            Terms of Service
          </a>
          {" "}and{" "}
          <a href="#" onClick={(e) => e.preventDefault()}>
            Privacy Policy
          </a>
        </p>
      </div>
    </div>
  );
}
