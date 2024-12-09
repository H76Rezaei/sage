import React, { useEffect, useState } from 'react';
import { MessageCircle, Mic, Type } from 'lucide-react';
import './MainPage.css';

const MainPage = ({ onSelectOption }) => {
  const [displayText, setDisplayText] = useState('');
  const fullText = "Hi, how can I help you today?";

  useEffect(() => {
    let currentIndex = 0;
    const intervalId = setInterval(() => {
      setDisplayText(fullText.slice(0, currentIndex + 1));
      currentIndex++;
      if (currentIndex === fullText.length) {
        clearInterval(intervalId);
      }
    }, 30); // Adjust the interval to control the speed of the animation

    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="container">
      <div className="chat-wrapper">
        {/* Conversation Icon and Welcome Message */}
        <div className="welcome-section">
          <MessageCircle className="message-icon" />
          <h1>{displayText}</h1>
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
