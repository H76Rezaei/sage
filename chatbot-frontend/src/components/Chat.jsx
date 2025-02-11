import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import TextareaAutosize from "react-textarea-autosize";
import { Send, Mic } from "lucide-react";
import Lottie from "lottie-react";

import animationData from "./Animation_logo.json";
import "./Chat.css";

const Chat = ({ sendConversation, saveToHistory, fontSize, fontFamily }) => {
  const [message, setMessage] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [chatStarted, setChatStarted] = useState(false);
  const streamedResponseRef = useRef("");

  const navigate = useNavigate();

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

  const handleVoiceClick = () => {
    navigate("/voice");
  };

  const handleClearChat = () => {
    setChatHistory([]);
    setChatStarted(false);
    setIsTyping(false);
  };

  return (
    <div className="chat-chat-container">
      {!chatStarted && chatHistory.length === 0 ? (
        <div className="chat-welcome-screen">
          <div className="chat-logo-container large">
            <img src="/image/logo.png" alt="App Logo" className="chat-logo" />
            <Lottie
              animationData={animationData}
              loop={true}
              className="chat-logo-animation"
            />
          </div>

          <div className="chat-input-container top">
            <TextareaAutosize
              className="chat-chat-input"
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
            <div className="chat-button-container">
              <button
                className="chat-icon-button"
                onClick={handleSend}
                disabled={!message.trim() || isTyping}
              >
                <Send />
              </button>
              <button className="chat-icon-button" onClick={handleVoiceClick}>
                <Mic />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="chat-chat-screen">
          <div className="chat-top-right">
            <div className="chat-logo-container small">
              <img src="/image/logo.png" alt="App Logo" className="chat-logo" />
              <Lottie
                animationData={animationData}
                loop={true}
                className="chat-logo-animation"
              />
            </div>

            <button className="chat-clear-button" onClick={handleClearChat}>
              Clear Chat
            </button>
          </div>

          <div className="chat-messages-container">
            {chatHistory.map((msg, index) => (
              <div
                key={index}
                className={`chat-message ${
                  msg.sender === "user"
                    ? "chat-user-message"
                    : "chat-bot-message"
                } ${msg.isPartial ? "partial-message" : ""}`}
                style={{ fontSize, fontFamily }}
              >
                {msg.text}
              </div>
            ))}
          </div>

          <div className="chat-input-container bottom">
            <TextareaAutosize
              className="chat-chat-input"
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
            <div className="chat-button-container">
              <button
                className="chat-icon-button"
                onClick={handleSend}
                disabled={!message.trim() || isTyping}
              >
                <Send />
              </button>
              <button className="chat-icon-button" onClick={handleVoiceClick}>
                <Mic />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chat;
