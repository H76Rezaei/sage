import React from "react";
import { ArrowLeft } from "lucide-react";
import "./VoiceHistory.css";

const VoiceHistory = ({ onSelectOption, chatHistory }) => {
  return (
    <div className="voice-history-container">
      {/* Header Section */}
      <div className="voice-history-header">
        {/* <button
          className="back-button"
          onClick={() => onSelectOption("voiceChat")}
        >
          <ArrowLeft />
        </button> */}
        <h1>Voice Chat</h1>
      </div>

      {/* Chat History Section */}
      <div className="messages-container">
        {chatHistory.map((msg, index) => (
          <div
            key={index}
            className={`message ${
              msg.sender === "user" ? "user-message" : "bot-message"
            }`}
          >
            {msg.type === "audio" ? (
              <audio controls src={msg.content} className="audio-player" />
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
