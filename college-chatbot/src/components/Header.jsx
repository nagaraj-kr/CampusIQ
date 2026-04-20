import "./Header.css";

export default function Header({ user, onLogin, onSignup, onLogout }) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <span className="logo-icon">🎓</span>
          <span className="logo-text">Campus<span className="logo-accent">IQ</span></span>
        </div>
        <span className="logo-tagline">AI College Advisor</span>
      </div>

      <nav className="header-right">
        {user ? (
          <div className="user-pill">
            <div className="user-avatar">{user.name?.[0]?.toUpperCase() || "U"}</div>
            <span className="user-name">{user.name}</span>
            <button className="btn-ghost" onClick={onLogout}>Sign out</button>
          </div>
        ) : (
          <div className="auth-btns">
            <button className="btn-ghost" onClick={onLogin}>Log in</button>
            <button className="btn-primary" onClick={onSignup}>Sign up</button>
          </div>
        )}
      </nav>
    </header>
  );
}
