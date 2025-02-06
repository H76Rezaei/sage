import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./Login.css";

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
      <div className="Login-card">
        <h2>Login</h2>
        {errorMsg && <div className="Login-error">{errorMsg}</div>}
        <form onSubmit={handleSubmit}>
          <div className="Login-group">
            <label>Email</label>
            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="Login-form-group">
            <label>Password</label>
            <input
              type="password"
              placeholder="Enter your password"
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
