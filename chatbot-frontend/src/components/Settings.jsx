import React, { useState, useEffect } from "react";
import "./Settings.css";

const Settings = ({ applySettings }) => {
  const [fontSize, setFontSize] = useState("16px");
  const [fontFamily, setFontFamily] = useState("Arial");

  useEffect(() => {
    const savedFontSize = localStorage.getItem("fontSize");
    const savedFontFamily = localStorage.getItem("fontFamily");

    if (savedFontSize) {
      setFontSize(savedFontSize);
    }
    if (savedFontFamily) {
      setFontFamily(savedFontFamily);
    }
  }, []);

  const handleSave = () => {
    applySettings({ fontSize, fontFamily });
    localStorage.setItem("fontSize", fontSize);
    localStorage.setItem("fontFamily", fontFamily);
    alert("Settings updated successfully!");
  };

  return (
    <div className="settings-container">
      <h1> Settings</h1>
      <div className="font">
        <h3>Chat Font : </h3>
        <div className="settings-item">
          <label htmlFor="font-size">Font Size:</label>
          <select
            id="font-size"
            value={fontSize}
            onChange={(e) => setFontSize(e.target.value)}
            className="settings-select"
          >
            <option value="14px">Small</option>
            <option value="16px">Default</option>
            <option value="18px">Large</option>
            <option value="20px"> Extra Large</option>
          </select>
        </div>

        <div className="settings-item">
          <label htmlFor="font-family">Font Family:</label>
          <select
            id="font-family"
            value={fontFamily}
            onChange={(e) => setFontFamily(e.target.value)}
            className="settings-select"
          >
            <option value="Arial">Arial</option>
            <option value="Verdana">Verdana</option>
            <option value="Courier New">Courier New</option>
            <option value="Times New Roman">Time New Roman</option>
            <option value="Roboto">Roboto</option>
          </select>
        </div>
      </div>

      <div className="voice">
        <div className="settings-item">
          <label htmlFor="gender-voice">Voice:</label>
          <select
            id="gender-voice"
            value={fontSize}
            className="settings-select"
          >
            <option value="Man">Man</option>
            <option value="Woman">Woman</option>
          </select>
        </div>
      </div>

      <button className="save-button" onClick={handleSave}>
        Apply Settings
      </button>
    </div>
  );
};

export default Settings;
