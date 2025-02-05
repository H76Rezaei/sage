import React, { useEffect, useState } from "react";
import { MessageCircle, Mic, Type } from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./Home.css";
import animationData from "./Animation_logo.json";
import Lottie from "lottie-react";

const MainPage = ({ fontSize, fontFamily }) => {
  const [displayText, setDisplayText] = useState("");
  const fullText = " How can I assist you today?";
  const navigate = useNavigate();

  // useEffect(() => {
  //   let currentIndex = 0;
  //   const intervalId = setInterval(() => {
  //     setDisplayText(fullText.slice(0, currentIndex + 1));
  //     currentIndex++;
  //     if (currentIndex === fullText.length) {
  //       clearInterval(intervalId);
  //     }
  //   }, 60);

  //   return () => clearInterval(intervalId);
  // }, []);

  return (
    <div className="home-main-container">
      <div className="home-main-container">
        <div className="home-welcome-screen">
          <div className="home-logo-container">
            <img src="/image/logo.png" alt="App Logo" className="home-logo" />
            <Lottie
              animationData={animationData}
              loop={true}
              className="home-logo-animation"
            />
          </div>
          <p className="home-welcome-text" style={{ fontSize, fontFamily }}>
            Hi, How can I help you Today?
          </p>
          <div className="home-button-container">
            <button className="home-button" onClick={() => navigate("/voice")}>
              <span>Voice Chat</span>
            </button>

            <button className="home-button" onClick={() => navigate("/chat")}>
              <span>Text Chat</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainPage;
