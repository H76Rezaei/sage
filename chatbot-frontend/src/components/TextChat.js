import React, { useState } from 'react';
import { ArrowLeft, Send } from 'lucide-react';
import './TextChat.css';

const TextChat = ({ onSelectOption, sendConversation }) => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = async () => {
    if (message.trim() && !isTyping) {
      const newMessage = { text: message, sender: 'user' };
      setChatHistory(prev => [...prev, newMessage]);
      setMessage('');
      setIsTyping(true);

      try {
        // Send user message to the backend and get the response
        const response = await sendConversation(message);

        // Update the chat history with the bot's response
        if (response && response.data) {
          const botMessage = { text: response.data.reply, sender: 'bot' };
          setChatHistory(prev => [...prev, botMessage]);
        }
      } catch (error) {
        console.error('Error communicating with the backend:', error);
        setChatHistory(prev => [...prev, { text: 'Error: Unable to get a response.', sender: 'bot' }]);
      } finally {
        setIsTyping(false);
      }
    }
  };

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <button className="back-button" onClick={() => onSelectOption(null)}>
          <ArrowLeft />
        </button>
        <h1>Text Chat</h1>
      </div>

      {/* Chat Messages */}
      <div className="messages-container">
        {chatHistory.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}
          >
            {msg.text}
          </div>
        ))}
      </div>

      {/* Input Area */}
      <div className="input-container">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message..."
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
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
