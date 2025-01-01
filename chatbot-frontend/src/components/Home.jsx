import React, { useEffect, useState } from "react";
import { MessageCircle, Mic, Type } from "lucide-react";
import { useNavigate } from "react-router-dom"; 
import "./Home.css";

const MainPage = () => {
  const [displayText, setDisplayText] = useState("");
  const fullText = " How can I assist you today?";
  const navigate = useNavigate(); 

  useEffect(() => {
    let currentIndex = 0;
    const intervalId = setInterval(() => {
      setDisplayText(fullText.slice(0, currentIndex + 1));
      currentIndex++;
      if (currentIndex === fullText.length) {
        clearInterval(intervalId);
      }
    }, 60);

    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="main-container">
      <div className="welcome-message">
        <h2> Hi,Welcome!</h2>
      </div>

      <div className="content-container">
        <div className="left-content">
          <div className="welcome-section">
            <MessageCircle className="message-icon" />
            <h1>{displayText}</h1>
          </div>

          <div className="button-container">
            <button className="button" onClick={() => navigate("/voice")}>
              <Mic className="icon" />
              <span>Voice Chat</span>
            </button>

            <button className="button" onClick={() => navigate("/chat")}>
              <Type className="icon" />
              <span>Text Chat</span>
            </button>
          </div>
        </div>

        <div className="right-image">
          <img src="/image/bot.png" alt="" />
        </div>
      </div>
    </div>
  );
};

export default MainPage;
