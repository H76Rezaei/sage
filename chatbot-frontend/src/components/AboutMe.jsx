import React from "react";
import "./AboutMe.css";

const AboutMe = () => {
  return (
    <div className="about-me-container">
      <h1 className="about-me-title">About Me</h1>

      <div className="about-me-section">
        <h2 className="about-me-subtitle">Who Am I?</h2>
        <p className="about-me-text">.............</p>
      </div>

      <div className="about-me-section">
        <h2 className="about-me-subtitle">How I Work</h2>
        <p className="about-me-text">------------</p>
      </div>

      <div className="about-me-section">
        <h2 className="about-me-subtitle">My Goals</h2>
        <p className="about-me-text">---------------</p>
      </div>

      <div className="about-me-section">
        <h2 className="about-me-subtitle">How to Use Me</h2>
        <p className="about-me-text">---------</p>
      </div>
    </div>
  );
};

export default AboutMe;
