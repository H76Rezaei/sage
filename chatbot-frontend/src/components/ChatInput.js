import React, { useState } from "react";
import PropTypes from "prop-types";

function ChatInput({ onSendMessage }) {
  const [message, setMessage] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      onSendMessage(message);
      setMessage("");
    }
  };

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type a message..."
        className="chat-input"
      />
      <button type="submit" className="send-button">
        Send
      </button>
    </form>
  );
}

ChatInput.propTypes = {
  onSendMessage: PropTypes.func.isRequired,
};

export default ChatInput;
