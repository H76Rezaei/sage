import React, { useState, useRef } from "react";
import { ArrowLeft, Send } from "lucide-react";
import "./Chat.css";

const TextChat = ({
  onSelectOption,
  sendConversation,
  saveToHistory,
  fontSize,
  fontFamily,
}) => {
  const [message, setMessage] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const streamedResponseRef = useRef("");

  const handleSend = async () => {
    if (message.trim() && !isTyping) {
      const userMessage = {
        text: message,
        sender: "user",
        id: Date.now(),
      };

      // Add user message to chat history
      setChatHistory((prev) => [...prev, userMessage]);
      saveToHistory(userMessage);

      const currentMessage = message;
      setMessage("");
      setIsTyping(true);
      streamedResponseRef.current = "";

      try {
        await sendConversation(currentMessage, (streamData) => {
          if (streamData.response) {
            streamedResponseRef.current += streamData.response;
          }

          // Update chat history
          setChatHistory((prevHistory) => {
            const newHistory = [...prevHistory];

            // Find existing bot message for this conversation
            const lastBotMessageIndex = newHistory.findLastIndex(
              (msg) =>
                msg.sender === "bot" && msg.conversationId === userMessage.id
            );

            const botMessage = {
              text: streamedResponseRef.current,
              sender: "bot",
              conversationId: userMessage.id, // Link to user message
              isPartial: !streamData.is_final,
              id: Date.now(), // Unique identifier
            };

            if (lastBotMessageIndex !== -1) {
              // Update existing bot message
              newHistory[lastBotMessageIndex] = botMessage;
            } else {
              // Add new bot message
              newHistory.push(botMessage);
            }

            return newHistory;
          });

          if (streamData.is_final) {
            saveToHistory({
              text: streamedResponseRef.current,
              sender: "bot",
            });
            setIsTyping(false);
          }
        });
      } catch (error) {
        console.error("Error communicating with the backend:", error);
        const errorMessage = {
          text: "Error: Unable to connect to the server. Please try again.",
          sender: "bot",
          id: Date.now(),
        };
        setChatHistory((prev) => [...prev, errorMessage]);
        saveToHistory(errorMessage);
        setIsTyping(false);
      }
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <button className="back-button" onClick={() => onSelectOption(null)}>
          <ArrowLeft />
        </button>
        <h1>Text Chat</h1>
      </div>

      <div className="messages-container">
        {chatHistory.map((msg, index) => (
          <div
            key={index}
            className={`message ${
              msg.sender === "user" ? "user-message" : "bot-message"
            } ${msg.isPartial ? "partial-message" : ""}`}
            style={{ fontSize, fontFamily }}
          >
            {msg.text}
          </div>
        ))}
      </div>

      <div className="input-container">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message..."
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
          disabled={isTyping}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={!message.trim() || isTyping}
        >
          <Send />
        </button>
      </div>
    </div>
  );
};

export default TextChat;
