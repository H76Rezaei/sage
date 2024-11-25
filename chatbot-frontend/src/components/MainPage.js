import React from 'react';
import { MessageCircle, Mic, Type } from 'lucide-react';
import './MainPage.css';

const MainPage = ({ onSelectOption }) => {
  return (
    <div className="container">
      <div className="chat-wrapper">
        {/* Conversation Icon and Welcome Message */}
        <div className="welcome-section">
          <MessageCircle className="message-icon" />
          <h1>Hi, how can I help you today?</h1>
        </div>

        {/* Buttons Container */}
        <div className="buttons-container">
          {/* Voice Chat Button */}
          <button className="chat-button" onClick={() => onSelectOption('voice')}>
            <Mic />
            <span>Voice Chat</span>
          </button>

          {/* Text Chat Button */}
          <button className="chat-button" onClick={() => onSelectOption('text')}>
            <Type />
            <span>Text Chat</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default MainPage;