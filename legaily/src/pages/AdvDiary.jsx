import React, { useState, useEffect } from "react";

const makeEntryId = () =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;

const AdvDiary = () => {
  const [form, setForm] = useState({
    matterNumber: "",
    partyName: "",
    date: "",
    time: "",
    ampm: "AM",
    notes: ""
  });

  const [entries, setEntries] = useState(() => {
    const saved = localStorage.getItem("advDiaryEntries");
    const parsed = saved ? JSON.parse(saved) : [];
    // Backfill ids for older saved entries
    return Array.isArray(parsed)
      ? parsed.map((e) => ({ id: e?.id || makeEntryId(), ...e }))
      : [];
  });

  const [showPopup, setShowPopup] = useState(false);
  const [dialogEntries, setDialogEntries] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const today = new Date();
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [currentYear, setCurrentYear] = useState(today.getFullYear());

  useEffect(() => {
    document.body.style.margin = 0;
    document.body.style.overflow = "hidden";
  }, []);

  useEffect(() => {
    localStorage.setItem("advDiaryEntries", JSON.stringify(entries));
  }, [entries]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (editingId) {
      const updated = { id: editingId, ...form };
      setEntries((prev) => prev.map((e) => (e.id === editingId ? updated : e)));
      setDialogEntries((prev) => prev.map((e) => (e.id === editingId ? updated : e)));
      setEditingId(null);
    } else {
      const newEntry = { id: makeEntryId(), ...form };
      setEntries((prev) => [...prev, newEntry]);
    }
    setShowPopup(true);
    setTimeout(() => setShowPopup(false), 2000);
    setForm({
      matterNumber: "",
      partyName: "",
      date: "",
      time: "",
      ampm: "AM",
      notes: ""
    });
  };

  const deleteEntryById = (id) => {
    if (!id) return;
    const ok = window.confirm("Delete this diary entry?");
    if (!ok) return;

    setEntries((prev) => prev.filter((e) => e.id !== id));
    setDialogEntries((prev) => prev.filter((e) => e.id !== id));
    if (editingId === id) {
      setEditingId(null);
      setForm({
        matterNumber: "",
        partyName: "",
        date: "",
        time: "",
        ampm: "AM",
        notes: ""
      });
    }
  };

  const startEditEntry = (entry) => {
    if (!entry?.id) return;
    setEditingId(entry.id);
    setDialogOpen(false);
    setForm({
      matterNumber: entry.matterNumber || "",
      partyName: entry.partyName || "",
      date: entry.date || "",
      time: entry.time || "",
      ampm: entry.ampm || "AM",
      notes: entry.notes || ""
    });
    // scroll to form area
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const isHighlighted = (day) =>
    entries.some((entry) => {
      const date = new Date(entry.date);
      return (
        date.getDate() === day &&
        date.getMonth() === currentMonth &&
        date.getFullYear() === currentYear
      );
    });

  const getEntriesByDate = (day) => {
    return entries.filter((entry) => {
      const date = new Date(entry.date);
      return (
        date.getDate() === day &&
        date.getMonth() === currentMonth &&
        date.getFullYear() === currentYear
      );
    });
  };

  const daysInMonth = (month, year) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (month, year) => new Date(year, month, 1).getDay();

  const handleMonthChange = (e) => setCurrentMonth(parseInt(e.target.value));
  const handleYearChange = (e) => setCurrentYear(parseInt(e.target.value));

  const renderCalendar = () => {
    const days = [];
    const totalDays = daysInMonth(currentMonth, currentYear);
    const firstDay = getFirstDayOfMonth(currentMonth, currentYear);
    let dayCounter = 1;

    for (let i = 0; i < 6; i++) {
      const week = [];
      for (let j = 0; j < 7; j++) {
        if ((i === 0 && j < firstDay) || dayCounter > totalDays) {
          week.push(<td key={j}></td>);
        } else {
          const highlight = isHighlighted(dayCounter);
          const dayEntries = getEntriesByDate(dayCounter);
          const tooltip = dayEntries.map(e => e.partyName).join(", ");
          week.push(
            <td
              key={j}
              title={tooltip}
              onClick={() => {
                if (dayEntries.length > 0) {
                  setDialogEntries(dayEntries);
                  setDialogOpen(true);
                }
              }}
              style={{
                padding: "14px",
                backgroundColor: highlight ? "#fde4b7" : "#fff",
                border: "1px solid #ddd",
                borderRadius: "4px",
                fontWeight: highlight ? "bold" : "normal",
                textAlign: "center",
                cursor: highlight ? "pointer" : "default",
                fontSize: "0.85rem",
              }}
            >
              <>
                {dayCounter}
                {highlight && (
                  <div
                    style={{
                      marginTop: 4,
                      background: "#ffbb73",
                      color: "#222",
                      fontSize: "0.65rem",
                      borderRadius: "4px",
                      padding: "2px 4px",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {tooltip}
                  </div>
                )}
              </>
            </td>
          );
          dayCounter++;
        }
      }
      days.push(<tr key={i}>{week}</tr>);
    }
    return days;
  };

  return (
    <>
      {/* Entry Added Popup */}
      {showPopup && (
        <div
          style={{
            position: "fixed",
            top: "20px",
            left: "50%",
            transform: "translateX(-50%)",
            background: "#d2691e",
            color: "white",
            padding: "10px 20px",
            borderRadius: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            zIndex: 9999,
            fontWeight: "500",
            fontSize: "1rem",
          }}
        >
          Entry added successfully!
        </div>
      )}

      {/* Dialog Box for Viewing Entries */}
      {dialogOpen && (
        <div
          style={{
            position: "fixed",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            background: "#fff",
            padding: "1rem 1.5rem",
            borderRadius: "12px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
            zIndex: 9999,
            width: "400px",
            maxHeight: "80vh",
            overflowY: "auto",
          }}
        >
          <h3 style={{ color: "#d2691e", marginBottom: "0.5rem" }}>Entries for this date</h3>
          {dialogEntries.map((entry, idx) => (
            <div key={entry.id || idx} style={{ borderBottom: "1px solid #ddd", marginBottom: "1rem", paddingBottom: "0.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.75rem" }}>
                <div style={{ fontWeight: 700, color: "#222" }}>
                  {entry.partyName || "Entry"}
                </div>
                <div style={{ display: "flex", gap: "0.4rem", flexShrink: 0 }}>
                  <button
                    type="button"
                    onClick={() => startEditEntry(entry)}
                    style={{
                      background: "#0d6efd",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      padding: "0.25rem 0.6rem",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                    }}
                    title="Edit entry"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteEntryById(entry.id)}
                    style={{
                      background: "#dc3545",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      padding: "0.25rem 0.6rem",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                    }}
                    title="Delete entry"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <p><strong>Matter No:</strong> {entry.matterNumber}</p>
              <p><strong>Party:</strong> {entry.partyName}</p>
              <p><strong>Time:</strong> {entry.time} {entry.ampm}</p>
              <p><strong>Notes:</strong> {entry.notes}</p>
            </div>
          ))}
          <button onClick={() => setDialogOpen(false)} style={{ ...submitButtonStyle, width: "100%" }}>
            Close
          </button>
        </div>
      )}

      {/* Layout */}
      <div
        style={{
          display: "flex",
          height: "100vh",
          padding: "1rem",
          gap: "1rem",
          background: "#f8f9fa",
          fontSize: "0.88rem",
          boxSizing: "border-box",
          overflow: "hidden",
        }}
      >
        {/* Entry Form */}
        <div
          style={{
            flex: 1,
            padding: "1rem",
            background: "#fff",
            borderRadius: "12px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <h1 style={{ marginBottom: "0.3rem", fontSize: "1.3rem" }}>Lawyer's Diary</h1>
          <h2 style={{ color: "#d2691e", marginBottom: "0.8rem", fontSize: "1rem" }}>
            {editingId ? "Update Entry" : "Add New Entry"}
          </h2>
          <form onSubmit={handleSubmit} style={{ flexGrow: 1 }}>
            <input type="text" name="matterNumber" placeholder="Matter Number" value={form.matterNumber} onChange={handleChange} style={cleanInputStyle} />
            <input type="text" name="partyName" placeholder="Party Name" value={form.partyName} onChange={handleChange} style={cleanInputStyle} />
            <input type="date" name="date" value={form.date} onChange={handleChange} style={cleanInputStyle} />
            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.8rem" }}>
              <input type="time" name="time" value={form.time} onChange={handleChange} style={{ ...cleanInputStyle, flex: 1 }} />
              <select name="ampm" value={form.ampm} onChange={handleChange} style={{ ...cleanInputStyle, flex: 0.5 }}>
                <option>AM</option>
                <option>PM</option>
              </select>
            </div>
            <textarea name="notes" placeholder="Additional Notes" value={form.notes} onChange={handleChange} style={{ ...cleanInputStyle, height: "70px", resize: "none" }} />
            <button type="submit" style={submitButtonStyle}>
              {editingId ? "Update Entry" : "Add Entry"}
            </button>
          </form>
        </div>

        {/* Calendar View */}
        <div
          style={{
            flex: 1.5,
            display: "flex",
            flexDirection: "column",
            padding: "1rem",
            background: "#fff",
            borderRadius: "12px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
            <h2 style={{ color: "#d2691e", fontSize: "1rem" }}>Calendar</h2>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <select value={currentMonth} onChange={handleMonthChange} style={{ ...cleanInputStyle, padding: "0.4rem" }}>
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i} value={i}>
                    {new Date(0, i).toLocaleString("default", { month: "short" })}
                  </option>
                ))}
              </select>
              <select value={currentYear} onChange={handleYearChange} style={{ ...cleanInputStyle, padding: "0.4rem" }}>
                {Array.from({ length: 20 }, (_, i) => {
                  const year = new Date().getFullYear() - 10 + i;
                  return <option key={year} value={year}>{year}</option>;
                })}
              </select>
            </div>
          </div>

          <div style={{ flexGrow: 1 }}>
            <table
              style={{
                width: "100%",
                height: "85%",
                borderCollapse: "collapse",
                tableLayout: "fixed",
                fontSize: "0.85rem",
              }}
            >
              <thead>
                <tr>
                  {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                    <th
                      key={day}
                      style={{
                        padding: "8px",
                        backgroundColor: "#ffefe0",
                        border: "1px solid #f0c99c",
                        fontWeight: "600",
                      }}
                    >
                      {day}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>{renderCalendar()}</tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
};

const cleanInputStyle = {
  width: "100%",
  padding: "0.45rem 0.5rem",
  marginBottom: "0.7rem",
  border: "none",
  borderBottom: "1px solid #ccc",
  backgroundColor: "#fdfdfd",
  fontSize: "1rem",
};

const submitButtonStyle = {
  background: "#d2691e",
  color: "#fff",
  padding: "0.45rem 1rem",
  border: "none",
  borderRadius: "5px",
  cursor: "pointer",
  fontSize: "0.88rem",
  fontWeight: "bold",
  marginTop: "1.5rem",
};

export default AdvDiary;
