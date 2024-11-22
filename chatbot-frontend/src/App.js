import React, { useState, useEffect } from 'react';
import ChatBox from './components/ChatBox';
import ChatInput from './components/ChatInput';
import VoiceRecorder from './components/VoiceRecorder';
import { sendConversation } from './services/textApi';
import './App.css';

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

    const botMessage = { type: "bot", text: "" };
    setMessages((prev) => [...prev, botMessage]);

    try {
      await sendConversation(text, (streamData) => {
        setMessages((prev) => {
          const updatedMessages = [...prev];
          updatedMessages[updatedMessages.length - 1] = {
            type: "bot",
            text: streamData.text,
          };
          return updatedMessages;
        });

        if (streamData.isFinal) {
          saveToHistory({ type: "bot", text: streamData.text });
        }
      });
    } finally {
      setLoading(false);
    }
  };

  const saveToHistory = (message) => {
    const history = JSON.parse(localStorage.getItem("chatHistory")) || [];
    history.push(message);
    localStorage.setItem("chatHistory", JSON.stringify(history));
  };

  const clearChatHistory = () => {
    localStorage.removeItem("chatHistory");
    setMessages([]);
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
