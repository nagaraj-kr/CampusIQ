import "./Intro.css";

const SUGGESTIONS = [
  "I scored 90 cutoff, looking for CS in Chennai",
  "Best engineering colleges under ₹1 Lakh fees",
  "MBA colleges near Coimbatore with hostel",
  "Colleges for Mechanical Engineering, budget ₹2L",
];

export default function Intro({ onSuggestion }) {
  return (
    <div className="intro">
      <div className="intro-badge">Powered by Llama 3.3 + Groq AI</div>

      <h1 className="intro-title">
        Find Your <span className="gradient-text">Perfect College</span>
        <br />in Tamil Nadu
      </h1>

      <p className="intro-desc">
        Tell me your cutoff score, preferred course, and budget — I'll recommend
        the best-fit colleges with AI-powered insights, distance analysis, and
        placement data.
      </p>

      <div className="suggestions">
        <p className="suggestions-label">Try asking</p>
        <div className="suggestion-grid">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              className="suggestion-chip"
              onClick={() => onSuggestion(s)}
            >
              <span className="chip-arrow">↗</span>
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="intro-stats">
        <div className="stat">
          <span className="stat-num">500+</span>
          <span className="stat-label">Colleges</span>
        </div>
        <div className="stat-divider" />
        <div className="stat">
          <span className="stat-num">AI</span>
          <span className="stat-label">Powered</span>
        </div>
        <div className="stat-divider" />
        <div className="stat">
          <span className="stat-num">Free</span>
          <span className="stat-label">Forever</span>
        </div>
      </div>
    </div>
  );
}
