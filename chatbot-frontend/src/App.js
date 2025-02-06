import React, { useState, useEffect } from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import "./App.css";

import Home from "./components/Home";
import Chat from "./components/Chat";
import Voice from "./components/Voice";
import Sidebar from "./components/Sidebar";
import Settings from "./components/Settings";
import VoiceHistory from "./components/VoiceHistory";
import AboutMe from "./components/AboutMe";
import MedicationReminder from "./components/MedicationReminder";
import Login from "./components/Login";
import Register from "./components/Register";
import ProtectedRoute from "./components/ProtectedRoute";

import { sendConversation } from "./services/textApi";
import { sendAudioToBackend } from "./services/speechApi";

function App() {
  const [chatHistory, setChatHistory] = useState([]);
  const [fontSize, setFontSize] = useState("18px");
  const [fontFamily, setFontFamily] = useState("Arial");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    const savedHistory = localStorage.getItem("chatHistory");
    if (savedHistory) {
      setChatHistory(JSON.parse(savedHistory));
    }
  }, []);

  const saveToHistory = (message) => {
    const updatedHistory = [...chatHistory, message];
    setChatHistory(updatedHistory);
    localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
  };

  const applySettings = (settings) => {
    setFontSize(settings.fontSize);
    setFontFamily(settings.fontFamily);
    localStorage.setItem("fontSize", settings.fontSize);
    localStorage.setItem("fontFamily", settings.fontFamily);
  };

  useEffect(() => {
    const savedFontSize = localStorage.getItem("fontSize");
    const savedFontFamily = localStorage.getItem("fontFamily");
    if (savedFontSize) setFontSize(savedFontSize);
    if (savedFontFamily) setFontFamily(savedFontFamily);
  }, []);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const LogoutButton = () => {
    const navigate = useNavigate();
    const handleLogout = () => {
      localStorage.removeItem("access_token");
      navigate("/login");
    };

    return (
      <button className="logout-button" onClick={handleLogout}>
        Logout
      </button>
    );
  };

  return (
    <Router>
      <div className="app-container">
        <div className="hamburger-menu" onClick={toggleSidebar}>
          ☰
        </div>
        <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
        <div className="content">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <div>
                    <Routes>
                      <Route
                        path="/"
                        element={
                          <Home
                            sendConversation={sendConversation}
                            saveToHistory={saveToHistory}
                            fontSize={fontSize}
                            fontFamily={fontFamily}
                          />
                        }
                      />
                      <Route
                        path="/chat"
                        element={
                          <Chat
                            sendConversation={sendConversation}
                            saveToHistory={saveToHistory}
                            fontSize={fontSize}
                            fontFamily={fontFamily}
                          />
                        }
                      />
                      <Route
                        path="/voice"
                        element={
                          <Voice
                            sendAudioToBackend={sendAudioToBackend}
                            saveToHistory={saveToHistory}
                            setChatHistory={setChatHistory}
                          />
                        }
                      />
                      <Route
                        path="/voice-history"
                        element={
                          <VoiceHistory
                            chatHistory={chatHistory}
                            onClearChat={() => setChatHistory([])}
                          />
                        }
                      />
                      <Route
                        path="/settings"
                        element={<Settings applySettings={applySettings} />}
                      />
                      <Route path="/about" element={<AboutMe />} />
                      <Route
                        path="/reminders"
                        element={<MedicationReminder />}
                      />
                    </Routes>
                  </div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
