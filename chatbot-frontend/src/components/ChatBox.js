import React from "react";
import PropTypes from "prop-types";

function ChatBox({ messages, loading }) {
  return (
    <div className="chat-box">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`message ${
            message.type === "user" ? "user-message" : "bot-message"
          }`}
        >
          {message.text}
        </div>
      ))}

      {loading && <div className="loading">Loading...</div>}
    </div>
  );
}

ChatBox.propTypes = {
  messages: PropTypes.array.isRequired,
  loading: PropTypes.bool.isRequired,
};

export default ChatBox;
