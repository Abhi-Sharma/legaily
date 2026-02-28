import React from "react";
import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import AdvDiary from "./pages/AdvDiary";
import judgepic from "./Assets/pic.png";
import ChatbotPage from './pages/ChatbotPage';
import DocAIPage from './pages/DocAIPage';
import DraftPage from "./pages/DraftPage";
import JudgeView from "./pages/JudgeView";
import LawyerView from "./pages/LawyerView";
import NotAuthorized from "./pages/NA";
import "./styles/Navbar.css"

const mainOrange = "#ff7a1a";
const darkOrange = "#ff6600";
const lightOrange = "#ffb380";

export default function Home({ user }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  return (
    <div
      style={{
        fontFamily: "Segoe UI, Arial, sans-serif",
        background: "#fff",
        minHeight: "100vh",
        margin: 0,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "24px 48px 0 48px",
        }}
      >
        <div
          style={{
            fontWeight: "bold",
            fontSize: " 2rem",
            color: darkOrange,
            fontFamily: "monospace",
            letterSpacing: "2px",
          }}
        >
          <span style={{ color: "#222" }}>Leg</span>
          <span style={{ color: mainOrange }}>ai</span>
          <span style={{ color: "#222" }}>ly</span>
        </div>

        {/* Nav */}
        <nav style={{ display: "flex", gap: 60 }}>
          <NavLink to="/" className="nav-link">Home</NavLink>
          <NavLink to="/docai" className="nav-link">Doc.AI</NavLink>
          <NavLink to="/query" className="nav-link">Query Page</NavLink>

          {/* Role-based view */}
          {user?.role === "judge" && <NavLink to="/judgeview" className="nav-link">Judge View</NavLink>}
          {user?.role === "lawyer" && <NavLink to="/lawyerview" className="nav-link">Lawyer View</NavLink>}

          <NavLink to="/drafts" className="nav-link">Drafts</NavLink>
        <NavLink
  to="/advdiary"
  className="nav-link"
  style={{ cursor: "pointer" }}
>
  Adv.Diary
</NavLink>

        </nav>

        {/* Profile + Logout */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            onClick={handleLogout}
            style={{
              border: `1.5px solid ${mainOrange}`,
              background: "#fff",
              color: mainOrange,
              borderRadius: 18,
              padding: "6px 20px",
              fontWeight: 500,
              cursor: "pointer",
              fontSize: "1rem",
            }}
          >
            Logout
          </button>
        </div>
      </header>

      {/* Decorative Circles */}
      <svg
        style={{
          position: "absolute",
          top: 70,
          right: 0,
          zIndex: 0,
          width: 520,
          height: 320,
          pointerEvents: "none",
        }}
      >
        <circle cx="440" cy="110" r="120" fill={mainOrange} fillOpacity="0.35" />
        <circle cx="520" cy="60" r="80" fill={mainOrange} fillOpacity="0.18" />
      </svg>

      {/* Main Content */}
      <main
        style={{
          padding: "48px 0 0 0",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          position: "relative",
          zIndex: 1,
          maxWidth: 1300,
          margin: "0 auto",
          flexGrow: 1,
        }}
      >
        <Routes>
          <Route
            path="/"
            element={
              <>
                <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                  <div style={{ flex: 1, minWidth: 350 }}>
                    <h1 style={{ fontSize: "4.2rem", fontWeight: 700, marginBottom: 12 }}>
                      Welcome to{" "}
                      <span>
                        Leg<span style={{ color: mainOrange }}>ai</span>ly
                      </span>
                    </h1>
                    <div
                      style={{
                        fontSize: "1.4rem",
                        color: "#444",
                        maxWidth: 540,
                        marginBottom: 10,
                        lineHeight: 1.5,
                      }}
                    >
                      Translate, summarize and simplify legal documents easily and
                      securely. Upload your document to receive accurate translations
                      and simplified summaries in your regional language. Powered by AI
                      and ML.
                    </div>
                    <button
                      onClick={() => navigate("/docai")}
                      style={{
                        background: mainOrange,
                        color: "#fff",
                        fontWeight: 600,
                        padding: "14px 32px",
                        borderRadius: "22px",
                        fontSize: "1.13rem",
                        border: "none",
                        cursor: "pointer",
                        marginBottom: "30px",
                        marginTop: "10px",
                        boxShadow: "0 2px 8px rgba(255,122,26,0.09)",
                      }}
                    >
                      Start Now
                    </button>
                  </div>
                  <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
                    <img
                      src={judgepic}
                      alt="Scales and gavel"
                      style={{
                        width: 600,
                        height: 350,
                        objectFit: "cover",
                        borderRadius: "28px",
                        boxShadow: "0 2px 16px rgba(0,0,0,0.09)",
                        border: "none",
                        marginTop: 100,
                        marginLeft: 100,
                      }}
                    />
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 40,
                    marginTop: "auto",
                    marginBottom: 60,
                    width: "100%",
                    justifyContent: "center",
                  }}
                >
                  <div style={featureCard}>Translate legal documents into any regional language</div>
                  <div style={featureCard}>Get simplified versions of your legal documents</div>
                  <div style={featureCard}>Find and view all case documents easily</div>
                </div>
              </>
            }
          />
          <Route path="/advdiary" element={<AdvDiary />} />
          <Route path="/query" element={<ChatbotPage />} />
          <Route path="/docai" element={<DocAIPage />} />
          <Route path="/drafts" element={<DraftPage />} />
          <Route path="/judgeview" element={user?.role === "judge" ? <JudgeView /> : <NotAuthorized />} />
          <Route path="/lawyerview" element={user?.role === "lawyer" ? <LawyerView /> : <NotAuthorized />} />
        </Routes>
      </main>
    </div>
  );
}

const featureCard = {
  background: "linear-gradient(90deg, #ff7a1a 80%, #ffb380 100%)",
  color: "#fff",
  borderRadius: 22,
  padding: "32px 24px",
  minWidth: 320,
  maxWidth: 400,
  fontSize: "1.2rem",
  fontWeight: 600,
  boxShadow: "0 2px 12px rgba(255,122,26,0.09)",
  textAlign: "center",
  zIndex: 1,
};
