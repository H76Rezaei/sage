import React, { useState, useEffect } from "react";
import ChatBox from "./components/ChatBox";
import ChatInput from "./components/ChatInput";
import ChatHistory from "./components/ChatHistory";
import sendToBackend from "./services/api";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const storedHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];
    setMessages(storedHistory);
  }, []);

  const handleSendMessage = async (text) => {
    const userMessage = { type: "user", text };
    setMessages((prev) => [...prev, userMessage]);
    saveToHistory(userMessage);

    setLoading(true);

    // Create an initial bot message
    const botMessage = { type: "bot", text: "" };
    setMessages((prev) => [...prev, botMessage]);

    try {
      await sendToBackend(text, (streamData) => {
        // Update the bot's message with the streamed text
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            type: "bot",
            text: streamData.text,
          };
          return newMessages;
        });

        // If this is the final chunk, save to history
        if (streamData.isFinal) {
          const finalBotMessage = {
            type: "bot",
            text: streamData.text,
          };
          saveToHistory(finalBotMessage);
        }
      });
    } finally {
      setLoading(false);
    }
  };

  const clearChatHistory = () => {
    localStorage.removeItem("chatHistory");
    setMessages([]);
  };

  const saveToHistory = (message) => {
    const history = JSON.parse(localStorage.getItem("chatHistory")) || [];
    history.push(message);
    localStorage.setItem("chatHistory", JSON.stringify(history));
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>Chatbot</h1>
        <button onClick={clearChatHistory}>Clear History</button>
      </header>
      <ChatBox messages={messages} loading={loading} />
      <ChatInput onSendMessage={handleSendMessage} />
      <VoiceRecorder onSendMessage={handleSendMessage} />
    </div>
  );
}

export default App;
