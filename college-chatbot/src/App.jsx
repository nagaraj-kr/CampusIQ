import { useState, useRef, useEffect } from "react";
import ChatWindow from "./components/ChatWindow";
import InputBar from "./components/InputBar";
import Header from "./components/Header";
import Intro from "./components/Intro";
import AuthModal from "./components/AuthModal";
import { generateBotResponse, buildResultMessage, buildErrorMessage } from "./chatFlow";
import { fetchRecommendations, resolveCoords, getCurrentUser, logoutUser } from "./api";
import "./App.css";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [chatStarted, setChatStarted] = useState(false);
  const [authModal, setAuthModal] = useState(null);
  const [user, setUser] = useState(null);
  const [studentData, setStudentData] = useState({});
  const [step, setStep] = useState(0);
  const [authLoading, setAuthLoading] = useState(true);
  const bottomRef = useRef(null);

  // Check if user is already logged in on component mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const currentUser = await getCurrentUser();
        if (currentUser) {
          setUser({
            username: currentUser.user.username,
            email: currentUser.user.email,
            name: currentUser.user.first_name || currentUser.user.username,
          });
        }
      } catch (err) {
        console.log("Not authenticated");
      } finally {
        setAuthLoading(false);
      }
    };

    checkAuth();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const addMessage = (role, content, type = "text", data = null) => {
    setMessages((prev) => [...prev, { role, content, type, data, id: Date.now() + Math.random() }]);
  };

  const sendMessage = async (text) => {
    if (!text.trim() || isTyping) return;

    // Prevent chat if not authenticated
    if (!user) {
      setAuthModal("login");
      return;
    }

    addMessage("user", text);
    setInputValue("");
    setChatStarted(true);
    setIsTyping(true);

    // Simulate network latency feel
    await new Promise((r) => setTimeout(r, 850 + Math.random() * 500));

    const { reply, nextStep, updatedData, isFetching } =
      await generateBotResponse(text, step, studentData);

    setStudentData(updatedData);
    setStep(nextStep);

    setIsTyping(false);
    addMessage("bot", reply);

    // If the pipeline just finished, hit the real Django API
    if (isFetching) {
      setIsTyping(true);
      try {
        const coords = resolveCoords(updatedData.location || "");
        const dataWithCoords = {
          ...updatedData,
          latitude: coords.lat,
          longitude: coords.lng,
        };
        const response = await fetchRecommendations(dataWithCoords);
        // Extract recommendations array from API response object
        const recommendations = response.recommendations || response;
        setIsTyping(false);
        addMessage("bot", buildResultMessage(recommendations), "recommendations", recommendations);
      } catch (err) {
        setIsTyping(false);
        addMessage("bot", buildErrorMessage(err));
      }
    }
  };

  const handleLogin = (userData) => {
    setUser(userData);
    setAuthModal(null);
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch (err) {
      console.error("Logout error:", err);
    }
    setUser(null);
    setMessages([]);
    setChatStarted(false);
    setStep(0);
    setStudentData({});
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="app">
        <div className="bg-grid" />
        <div className="bg-glow" />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
          <div style={{ textAlign: "center" }}>
            <p style={{ fontSize: "18px", color: "var(--text-secondary)" }}>Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show authentication prompt if not logged in
  if (!user) {
    return (
      <div className="app">
        <div className="bg-grid" />
        <div className="bg-glow" />

        <Header
          user={user}
          onLogin={() => setAuthModal("login")}
          onSignup={() => setAuthModal("signup")}
          onLogout={handleLogout}
        />

        <main className="main" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ textAlign: "center", maxWidth: "500px" }}>
            <div style={{ fontSize: "64px", marginBottom: "24px" }}>🔐</div>
            <h2 style={{ fontSize: "28px", marginBottom: "12px", color: "var(--text-primary)" }}>
              Welcome to CampusIQ
            </h2>
            <p style={{ fontSize: "16px", color: "var(--text-secondary)", marginBottom: "32px", lineHeight: "1.6" }}>
              Sign in or create an account to get started with personalized college recommendations.
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
              <button
                onClick={() => setAuthModal("login")}
                style={{
                  padding: "12px 28px",
                  background: "var(--accent)",
                  color: "white",
                  border: "none",
                  borderRadius: "10px",
                  fontSize: "15px",
                  fontWeight: "600",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
                onMouseOver={(e) => (e.target.style.background = "#5a7ce8")}
                onMouseOut={(e) => (e.target.style.background = "var(--accent)")}
              >
                Sign In
              </button>
              <button
                onClick={() => setAuthModal("signup")}
                style={{
                  padding: "12px 28px",
                  background: "var(--surface-2)",
                  color: "var(--text-primary)",
                  border: "1.5px solid var(--border)",
                  borderRadius: "10px",
                  fontSize: "15px",
                  fontWeight: "600",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
                onMouseOver={(e) => (e.target.style.background = "var(--border)")}
                onMouseOut={(e) => (e.target.style.background = "var(--surface-2)")}
              >
                Sign Up
              </button>
            </div>
          </div>
        </main>

        {authModal && (
          <AuthModal
            mode={authModal}
            onClose={() => setAuthModal(null)}
            onLogin={handleLogin}
            onSwitchMode={(m) => setAuthModal(m)}
          />
        )}
      </div>
    );
  }

  return (
    <div className="app">
      <div className="bg-grid" />
      <div className="bg-glow" />

      <Header
        user={user}
        onLogin={() => setAuthModal("login")}
        onSignup={() => setAuthModal("signup")}
        onLogout={handleLogout}
      />

      <main className="main">
        {!chatStarted ? (
          <Intro onSuggestion={(t) => sendMessage(t)} />
        ) : (
          <ChatWindow messages={messages} isTyping={isTyping} bottomRef={bottomRef} />
        )}
      </main>

      <div className="input-zone">
        <InputBar
          value={inputValue}
          onChange={setInputValue}
          onSend={sendMessage}
          disabled={isTyping}
          placeholder={
            step === 0
              ? "Tell me your cutoff score or ask anything about colleges..."
              : step >= 5
                ? "Ask about placements, fees, or type 'restart'..."
                : "Type your answer..."
          }
        />
        <p className="input-hint">
          CampusIQ may produce inaccurate results. Always verify college details independently.
        </p>
      </div>

      {authModal && (
        <AuthModal
          mode={authModal}
          onClose={() => setAuthModal(null)}
          onLogin={handleLogin}
          onSwitchMode={(m) => setAuthModal(m)}
        />
      )}
    </div>
  );
}
