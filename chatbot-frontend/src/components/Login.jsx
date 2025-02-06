import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./Login.css";
import animationData from "./Animation_logo.json";
import Lottie from "lottie-react";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    try {
      const response = await fetch("http://localhost:8000/user/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        setErrorMsg(data.detail || "An error occurred.");
        return;
      }
      localStorage.setItem("access_token", data.access_token);
      navigate("/");
    } catch (error) {
      console.error("Login error:", error);
      setErrorMsg("An error occurred.");
    }
  };

  return (
    <div className="Login-container">
      <div className="home-logo-container">
        <img src="/image/logo.png" alt="App Logo" className="home-logo" />
        <Lottie
          animationData={animationData}
          loop={true}
          className="home-logo-animation"
        />
      </div>
      <div className="Login-card">
        <h2>Login</h2>
        {errorMsg && <div className="Login-error">{errorMsg}</div>}
        <form onSubmit={handleSubmit}>
          <div className="Login-form-group">
            <input
              type="email"
              placeholder="   Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="Login-form-group">
            <input
              type="password"
              placeholder="   Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="Login-button">
            Login
          </button>
        </form>
        <p>
          New user?{" "}
          <Link to="/register" className="Login-link">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
