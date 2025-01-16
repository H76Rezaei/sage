import React from "react";
import { Link } from "react-router-dom";
import "./Sidebar.css";

const Sidebar = ({ isOpen, toggleSidebar }) => {
  return (
    <div className={`sidebar ${isOpen ? "open" : ""}`}>
      {/* Close Button for Mobile */}
      {isOpen && (
        <button className="closeButton" onClick={toggleSidebar}>
          ×
        </button>
      )}

      <div className="topSection">
        <ul className="menu">
          <li>
            <Link to="/" className="link" onClick={toggleSidebar}>
              🏠 Home
            </Link>
          </li>
          <li>
            <Link to="/chat" className="link" onClick={toggleSidebar}>
              💬 Chat with Me
            </Link>
          </li>
          <li>
            <Link to="/voice" className="link" onClick={toggleSidebar}>
              🗣️ Talk to Me
            </Link>
          </li>
          <li>
            <Link to="/settings" className="link" onClick={toggleSidebar}>
              ⚙️ Settings
            </Link>
          </li>
          <li>
            <Link to="/reminders" className="link" onClick={toggleSidebar}>
              💊 Medication Reminders
            </Link>
          </li>
          <li>
            <Link to="/about" className="link" onClick={toggleSidebar}>
              📜 About Me
            </Link>
          </li>
          <li>
            <Link to="/contact" className="link" onClick={toggleSidebar}>
              📞 Contact Us
            </Link>
          </li>
        </ul>
      </div>

      <div className="bottomSection">
        <div className="profile">
          <img
            src="https://via.placeholder.com/50"
            alt="User Avatar"
            className="avatar"
          />
          <p>Guest User</p>
        </div>
        <button className="loginButton">Login/Sign Up</button>
      </div>
    </div>
  );
};

export default Sidebar;
