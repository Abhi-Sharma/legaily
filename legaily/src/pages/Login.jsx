import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./Login.css";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const mainOrange = "#ff7a1a";
  const darkOrange = "#ff6600";

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch("http://localhost:5001/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      console.log("Login response:", data);

      if (response.ok) {
        localStorage.setItem("token", data.token);
        localStorage.setItem("role", data.user.role);
        localStorage.setItem("username", data.user.username);

        if (onLogin) onLogin();

        navigate("/");
      } else {
        alert(data.message || "Login failed");
      }
    } catch (error) {
      alert("Network error. Please try again later.");
      console.error(error);
    }
  };

  return (
    <div
      className="login-page"
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        fontFamily: "Segoe UI, Arial, sans-serif",
        position: "relative",
      }}
    >
      {/* Decorative floating circles */}
      <div className="login-decor-circle" />
      <div className="login-decor-circle" />
      <div className="login-decor-circle" />
      <div className="login-decor-circle" />
      <div className="login-decor-circle" />

      {/* Legal-themed icons (scales, gavel, document) */}
      <div className="login-legal-icons">⚖️</div>
      <div className="login-legal-icons">📜</div>
      <div className="login-legal-icons">⚖️</div>
      <div className="login-legal-icons">📋</div>

      {/* Large decorative SVG circles (like Home page) */}
      <svg
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: 480,
          height: 400,
          pointerEvents: "none",
          zIndex: 0,
        }}
      >
        <circle cx="380" cy="100" r="140" fill={mainOrange} fillOpacity="0.2" />
        <circle cx="420" cy="60" r="90" fill={darkOrange} fillOpacity="0.12" />
        <circle cx="340" cy="180" r="60" fill={mainOrange} fillOpacity="0.1" />
      </svg>
      <svg
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: 350,
          height: 300,
          pointerEvents: "none",
          zIndex: 0,
        }}
      >
        <circle cx="80" cy="220" r="100" fill={mainOrange} fillOpacity="0.15" />
        <circle cx="120" cy="260" r="50" fill={darkOrange} fillOpacity="0.1" />
      </svg>

      {/* Login form card */}
      <form
        onSubmit={handleSubmit}
        className="login-form-card"
        style={{
          background: "rgba(255, 255, 255, 0.95)",
          backdropFilter: "blur(12px)",
          border: `2px solid ${mainOrange}`,
          borderRadius: 20,
          padding: "40px 36px",
          width: 380,
          boxShadow: "0 8px 32px rgba(255, 122, 26, 0.15)",
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Legaily branding */}
        <div className="login-brand">
          <h1 style={{ margin: 0, fontSize: "2rem", fontWeight: 700, fontFamily: "monospace" }}>
            <span style={{ color: "#222" }}>Leg</span>
            <span style={{ color: mainOrange }}>ai</span>
            <span style={{ color: "#222" }}>ly</span>
          </h1>
          <p className="login-tagline">AI-Powered Legal Assistance</p>
        </div>

        <h2 style={{ color: mainOrange, marginBottom: 24, fontSize: "1.4rem" }}>Welcome back</h2>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 6, color: "#333", fontWeight: 500 }}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="your@email.com"
            style={{
              width: "100%",
              padding: 12,
              borderRadius: 10,
              border: "1px solid #ddd",
              fontSize: "1rem",
              boxSizing: "border-box",
            }}
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <label style={{ display: "block", marginBottom: 6, color: "#333", fontWeight: 500 }}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="••••••••"
            style={{
              width: "100%",
              padding: 12,
              borderRadius: 10,
              border: "1px solid #ddd",
              fontSize: "1rem",
              boxSizing: "border-box",
            }}
          />
        </div>

        <button
          type="submit"
          style={{
            width: "100%",
            padding: "14px 0",
            background: `linear-gradient(135deg, ${mainOrange} 0%, ${darkOrange} 100%)`,
            color: "#fff",
            border: "none",
            borderRadius: 10,
            fontSize: "1.1rem",
            fontWeight: 600,
            cursor: "pointer",
            marginBottom: 16,
            boxShadow: "0 4px 14px rgba(255, 122, 26, 0.4)",
          }}
        >
          Login
        </button>

        <div style={{ textAlign: "center" }}>
          <span style={{ fontSize: "0.9rem", color: "#666" }}>Don't have an account? </span>
          <Link
            to="/signup"
            style={{
              color: mainOrange,
              textDecoration: "none",
              fontWeight: "bold",
            }}
          >
            Sign Up
          </Link>
        </div>
      </form>
    </div>
  );
}
