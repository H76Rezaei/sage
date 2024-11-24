import React, { useState, useRef } from 'react';
import { ArrowLeft, Send } from 'lucide-react';
import './TextChat.css';

//added saveToHistory to method parameters
const TextChat = ({ onSelectOption, sendConversation, saveToHistory }) => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  // added a const: currentResponseRef
  const currentResponseRef = useRef('');

  const handleSend = async () => {
    if (message.trim() && !isTyping) {
      //renamed const newMessage to userMessage
      const userMessage = { text: message, sender: 'user' };
      setChatHistory(prev => [...prev, userMessage]);
      //used saveToHistory()
      saveToHistory(userMessage);
      

      // updated this part to handle backend chunk by chunk streaming:

      const currentMessage = message;
      setMessage('');
      setIsTyping(true);
      currentResponseRef.current = '';

      try {
        await sendConversation(currentMessage, (data) => {
          if (data.response) {
            currentResponseRef.current = data.response;
            
            // Update chat history with the current accumulated response
            setChatHistory(prev => {
              const newHistory = prev.filter(msg => 
                !(msg.sender === 'bot' && msg.isPartial)
              );
              return [...newHistory, {
                text: currentResponseRef.current,
                sender: 'bot',
                isPartial: !data.is_final
              }];
            });

            // Save to history only when the response is final
            if (data.is_final) {
              saveToHistory({
                text: currentResponseRef.current,
                sender: 'bot'
              });
            }
          }
        });
      } catch (error) {
        console.error('Error communicating with the backend:', error);
        const errorMessage = { 
          text: 'Error: Unable to connect to the server. Please try again.',
          sender: 'bot'
        };
        setChatHistory(prev => [...prev, errorMessage]);
        saveToHistory(errorMessage);
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
