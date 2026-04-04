import React, { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, Link } from "react-router-dom";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import NotAuthorized from "./pages/NA";
import Home from "./Home";

function AuthTopBar() {
  const location = useLocation();
  const showBar = location.pathname === "/login" || location.pathname === "/signup";
  if (!showBar) return null;

  return (
    <header
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        height: 56,
        background: "#ff7a1a",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        zIndex: 1000,
      }}
    >
      <Link to="/login" style={{ color: "#fff", textDecoration: "none", fontSize: "22px", fontWeight: 700 }}>
        legAily
      </Link>
      <nav style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <Link
          to="/login"
          style={{
            color: "#fff",
            textDecoration: "none",
            padding: "8px 20px",
            borderRadius: 8,
            background: location.pathname === "/login" ? "rgba(255,255,255,0.25)" : "transparent",
            fontWeight: 600,
          }}
        >
          Login
        </Link>
        <Link
          to="/signup"
          style={{
            color: "#fff",
            textDecoration: "none",
            padding: "8px 20px",
            borderRadius: 8,
            background: location.pathname === "/signup" ? "rgba(255,255,255,0.25)" : "transparent",
            fontWeight: 600,
          }}
        >
          Sign up
        </Link>
      </nav>
    </header>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const username = localStorage.getItem("username");

    if (token && role && username) {
      setUser({ token, role, username });
    }
    setAuthChecked(true);
  }, []);

  const handleLogin = () => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const username = localStorage.getItem("username");

    if (token && role && username) {
      setUser({ token, role, username });
    }
  };

  // Don't redirect to login until we've read auth from localStorage (fixes refresh)
  const requireAuth = (element) => {
    if (!authChecked) {
      return (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#fff8f0" }}>
          <span style={{ color: "#ff8c00", fontSize: "18px" }}>Loading…</span>
        </div>
      );
    }
    return user ? element : <Navigate to="/login" replace />;
  };

  function Layout({ children }) {
    const location = useLocation();
    const isAuthPage = location.pathname === "/login" || location.pathname === "/signup";
    return <div style={{ paddingTop: isAuthPage ? 56 : 0 }}>{children}</div>;
  }

  return (
    <Router>
      <AuthTopBar />
      <Layout>
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/not-authorized" element={<NotAuthorized />} />
          <Route path="/*" element={requireAuth(<Home user={user} />)} />
        </Routes>
      </Layout>
    </Router>
  );
}
