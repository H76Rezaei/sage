import React from "react";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./VoiceHistory.css";

const VoiceHistory = ({ onSelectOption, chatHistory, onClearChat }) => {
  const navigate = useNavigate();
  return (
    <div className="voice-history-container">
      {/* Header Section */}
      <div className="voice-history-header">
        <button
          className="voice-history-back-button"
          onClick={() => navigate("/voice")}
        >
          <ArrowLeft />
        </button>
        <button className="voice-history-clear-button" onClick={onClearChat}>
          Clear Chat
        </button>
      </div>

      {/* Chat History Section */}
      <div className="voice-history-messages-container">
        {chatHistory.map((msg, index) => (
          <div
            key={index}
            className={`voice-history-message ${
              msg.sender === "user"
                ? "voice-history-user-message"
                : "voice-history-bot-message"
            }`}
          >
            {msg.type === "audio" ? (
              <audio
                controls
                src={msg.content}
                className="voice-history-audio-player"
              />
            ) : (
              msg.content
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default VoiceHistory;
