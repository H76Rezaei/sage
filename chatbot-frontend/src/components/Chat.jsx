import React, { useState, useRef } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { Send } from "lucide-react";
import "./Chat.css";
import animationData from "./Animation_logo.json";
import Lottie from "lottie-react";

const Chat = ({ sendConversation, saveToHistory, fontSize, fontFamily }) => {
  const [message, setMessage] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [chatStarted, setChatStarted] = useState(false);
  const streamedResponseRef = useRef("");

  const handleSend = async () => {
    if (!message.trim() || isTyping) return;

    if (!chatStarted) {
      setChatStarted(true);
    }

    const userMessage = {
      text: message,
      sender: "user",
      id: Date.now(),
    };

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

        setChatHistory((prevHistory) => {
          const newHistory = [...prevHistory];
          const lastBotMessageIndex = newHistory.findIndex(
            (msg) =>
              msg.sender === "bot" && msg.conversationId === userMessage.id
          );

          const botMessage = {
            text: streamedResponseRef.current,
            sender: "bot",
            conversationId: userMessage.id,
            isPartial: !streamData.is_final,
            id: Date.now(),
          };

          if (lastBotMessageIndex !== -1) {
            newHistory[lastBotMessageIndex] = botMessage;
          } else {
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
  };

  return (
    <div className="chat-container">
      {!chatStarted && chatHistory.length === 0 ? (
        <div className="welcome-screen">
          <div className="logo-container">
            <img src="/image/logo.png" alt="App Logo" className="logo" />
            <Lottie
              animationData={animationData}
              loop={true}
              className="logo-animation"
            />
          </div>
          <p className="welcome-text" style={{ fontSize, fontFamily }}>
            How can I help you?
          </p>
          <div className="input-container top">
            <TextareaAutosize
              className="chat-input"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isTyping}
              style={{ fontSize, fontFamily }}
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
      ) : (
        <div className="chat-screen">
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
          <div className="input-container bottom">
            <TextareaAutosize
              className="chat-input"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isTyping}
              style={{ fontSize, fontFamily }}
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
      )}
    </div>
  );
};

export default Chat;
