import { useRef, useEffect } from "react";
import "./InputBar.css";

export default function InputBar({ value, onChange, onSend, disabled, placeholder }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [value]);

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend(value);
    }
  };

  return (
    <div className="input-bar-wrap">
      <div className={`input-bar ${disabled ? "input-disabled" : ""}`}>
        <textarea
          ref={textareaRef}
          className="input-field"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
        />
        <button
          className={`send-btn ${value.trim() && !disabled ? "send-active" : ""}`}
          onClick={() => !disabled && value.trim() && onSend(value)}
          disabled={disabled || !value.trim()}
          aria-label="Send"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  );
}
