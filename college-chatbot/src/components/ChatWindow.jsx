import "./ChatWindow.css";
import { useEffect } from "react";
import { RecommendationsList } from "./RecommendationsList";

function parseMarkdown(text) {
  // Debug: log incoming text to see if images are in the message
  if (text.includes('![')) {
    console.log('📸 Image markdown detected:', text.substring(0, 200));
  }
  
  // Handle images: ![alt](url)
  let html = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
    console.log('🖼️ Converting image:', { alt, url });
    return `<img src="${url}" alt="${alt}" data-college="${alt}" style="width:100%; height:280px; object-fit:cover; border-radius:8px; margin:8px 0; display:block;" />`;
  });
  
  // Handle links: [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
    console.log('🔗 Converting link:', { text, url });
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" style="color:#3b82f6; text-decoration:underline; cursor:pointer;">${text}</a>`;
  });
  
  // Handle bold: **text**
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  
  // Handle italic: *text*
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  
  // Handle line breaks
  html = html.replace(/\n/g, "<br/>");
  
  return html;
}

function TypingDots() {
  return (
    <div className="message bot-message">
      <div className="bot-avatar">🎓</div>
      <div className="bubble typing-bubble">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, isTyping, bottomRef }) {
  useEffect(() => {
    // Find all images and attach error handlers
    const images = document.querySelectorAll('img[data-college]');
    images.forEach((img) => {
      img.onerror = function() {
        console.warn(`⚠️ Image failed to load for: ${img.getAttribute('data-college')}`);
        
        // Generate SVG fallback card
        const collegeName = img.getAttribute('data-college');
        const colors = ['#1a472a', '#0066cc', '#cc3300', '#660066', '#006b4d', '#4a1a1a'];
        const colorIndex = collegeName.charCodeAt(0) % colors.length;
        const color = colors[colorIndex];
        
        const svg = `
          <svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
            <rect width="600" height="400" fill="${color}"/>
            <text x="50%" y="50%" font-size="48" font-weight="bold" fill="white" text-anchor="middle" dominant-baseline="middle" font-family="Arial, sans-serif">
              ${collegeName}
            </text>
          </svg>
        `;
        
        const dataUri = `data:image/svg+xml;base64,${btoa(svg)}`;
        img.src = dataUri;
        img.style.backgroundColor = color;
        console.log(`✅ Replaced with SVG fallback for: ${collegeName}`);
      };
    });
  }, [messages]); // Re-run when messages change
  
  return (
    <div className="chat-window">
      <div className="messages-list">
        {messages.map((msg) => {
          if (msg.type === "recommendations" && msg.data) {
            return (
              <div key={msg.id} className="message bot-message">
                <div className="bot-avatar">🎓</div>
                <div className="bubble recommendations-bubble">
                  <RecommendationsList
                    recommendations={msg.data}
                    loading={false}
                    error={null}
                  />
                </div>
              </div>
            );
          }
          return (
            <div
              key={msg.id}
              className={`message ${msg.role === "user" ? "user-message" : "bot-message"}`}
            >
              {msg.role === "bot" && <div className="bot-avatar">🎓</div>}
              <div
                className="bubble"
                dangerouslySetInnerHTML={{ __html: parseMarkdown(msg.content) }}
                style={{ wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}
              />
              {msg.role === "user" && <div className="user-avatar">U</div>}
            </div>
          );
        })}
        {isTyping && <TypingDots />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
