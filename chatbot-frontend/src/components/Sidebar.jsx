import React from "react";
import { Link } from "react-router-dom";
import "./Sidebar.css"; // Import the CSS file

const Sidebar = ({ isOpen, toggleSidebar }) => {
  return (
    <div className="sidebar">
      <div className="topSection">
        <ul className="menu">
          <li>
            <Link to="/" className="link">
              🏠 Home
            </Link>
          </li>
          <li>
            <Link to="/chat" className="link">
              💬 Chat with Me
            </Link>
          </li>
          <li>
            <Link to="/voice" className="link">
              🗣️ Talk to Me
            </Link>
          </li>
          <li>
            <Link to="/settings" className="link">
              ⚙️ Settings
            </Link>
          </li>
          <li>
            <Link to="/reminders" className="link">
              💊 Medication Reminders
            </Link>
          </li>
          <li>
            <Link to="/about" className="link">
              📜 About Me
            </Link>
          </li>
          <li>
            <Link to="/contact" className="link">
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
