import React from "react";
import { FaPlay } from "react-icons/fa"; // Play icon for the button

const ChatBox = ({ messages, loading }) => {
  const handlePlayMessage = async (text) => {
    try {
      await sendToBackend(text, null, true);
    } catch (error) {
      console.error("Error playing the message:", error);
    }
  };

  return (
    <div className="chat-box">
      {messages.map((message, index) => (
        <div key={index} className={`message ${message.type}`}>
          <div className="message-text">{message.text}</div>

          {message.type === "bot" && (
            <button onClick={() => handlePlayMessage(message.text)}>
              <FaPlay size={20} />
            </button>
          )}
        </div>
      ))}

      {loading && <div className="loading">Sage is typing...</div>}
    </div>
  );
};

export default ChatBox;
