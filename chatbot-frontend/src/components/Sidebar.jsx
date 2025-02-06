import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Sidebar.css";

const Sidebar = ({ isOpen, toggleSidebar }) => {
  const navigate = useNavigate();
  const token = localStorage.getItem("access_token");
  const [userName, setUserName] = useState("");

  // Fetch user profile to get user's name if token exists
  useEffect(() => {
    const fetchUserProfile = async () => {
      if (token) {
        try {
          const response = await fetch("http://localhost:8000/profile", {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          });
          if (!response.ok) {
            throw new Error("Failed to fetch profile");
          }
          const data = await response.json();
          // Combine first name and last name
          setUserName(`${data.first_name} ${data.last_name}`);
        } catch (error) {
          console.error("Error fetching profile:", error);
        }
      }
    };
    fetchUserProfile();
  }, [token]);

  // Handle authentication button click:
  // If token exists, perform logout, otherwise navigate to login
  const handleAuthClick = () => {
    toggleSidebar();
    if (token) {
      localStorage.removeItem("access_token");
      navigate("/login");
    } else {
      navigate("/login");
    }
  };

  // When clicking on the profile area, navigate to the profile page if logged in
  const handleProfileClick = () => {
    if (token) {
      toggleSidebar();
      navigate("/profile");
    }
  };

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
        <div
          className="profile"
          onClick={handleProfileClick}
          style={{ cursor: token ? "pointer" : "default" }}
        >
          <p>{token ? userName || "Loading..." : "Guest User"}</p>
        </div>
        <button className="loginButton" onClick={handleAuthClick}>
          {token ? "Logout" : "Login"}
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
