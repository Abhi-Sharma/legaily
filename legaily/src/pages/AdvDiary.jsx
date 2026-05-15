import React, { useState, useEffect } from "react";
import "./AdvDiary.css";

const API_BASE = "http://localhost:5001/api/diary";

const AdvDiary = () => {
  const [form, setForm] = useState({
    caseNumber: "",
    partyName: "",
    date: "",
    time: "",
    ampm: "AM",
    notes: ""
  });

  const [entries, setEntries] = useState([]);
  const [showPopup, setShowPopup] = useState(false);
  const [dialogEntries, setDialogEntries] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [viewingDoc, setViewingDoc] = useState(null);

  const today = new Date();
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [currentYear, setCurrentYear] = useState(today.getFullYear());

  useEffect(() => {
    document.body.style.margin = 0;
    document.body.style.backgroundColor = "#fff8f0";
    fetchEntries();
    return () => {
      document.body.style.backgroundColor = "";
    };
  }, []);

  const fetchEntries = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;
      const res = await fetch(`${API_BASE}/all`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        // Format to map _id to id for backwards UI compatibility
        setEntries(data.map(e => ({ ...e, id: e._id })));
      }
    } catch (err) {
      console.error("Failed to fetch diary entries:", err);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("token");
    if (!token) {
      alert("Please login first.");
      return;
    }

    try {
      if (editingId) {
        const res = await fetch(`${API_BASE}/update/${editingId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify(form)
        });
        if (res.ok) {
          const updated = await res.json();
          // Map _id -> id
          const fmtUpdated = { ...updated, id: updated._id };
          setEntries((prev) => prev.map((en) => (en.id === editingId ? fmtUpdated : en)));
          setDialogEntries((prev) => prev.map((en) => (en.id === editingId ? fmtUpdated : en)));
          setEditingId(null);
          
          setShowPopup(true);
          setTimeout(() => setShowPopup(false), 2500);
          setForm({
            caseNumber: "",
            partyName: "",
            date: "",
            time: "",
            ampm: "AM",
            notes: ""
          });
        } else {
          const errorData = await res.json();
          alert(`Failed to update: ${errorData.message || res.statusText}`);
        }
      } else {
        const res = await fetch(`${API_BASE}/create`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify(form)
        });
        if (res.ok) {
          const newEntry = await res.json();
          setEntries((prev) => [...prev, { ...newEntry, id: newEntry._id }]);
          
          setShowPopup(true);
          setTimeout(() => setShowPopup(false), 2500);
          setForm({
            caseNumber: "",
            partyName: "",
            date: "",
            time: "",
            ampm: "AM",
            notes: ""
          });
        } else {
          const errorData = await res.json();
          alert(`Failed to create: ${errorData.message || res.statusText}`);
        }
      }
    } catch (err) {
      console.error("Submit error:", err);
      alert("Failed to save entry.");
    }
  };

  const deleteEntryById = async (id) => {
    if (!id) return;
    const ok = window.confirm("Are you sure you want to delete this diary entry?");
    if (!ok) return;

    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`${API_BASE}/delete/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        setEntries((prev) => prev.filter((e) => e.id !== id));
        setDialogEntries((prev) => prev.filter((e) => e.id !== id));
        if (editingId === id) {
          setEditingId(null);
          setForm({
            caseNumber: "",
            partyName: "",
            date: "",
            time: "",
            ampm: "AM",
            notes: ""
          });
        }
        if (dialogEntries.length <= 1) {
          setDialogOpen(false);
        }
      }
    } catch (err) {
      console.error("Delete error:", err);
    }
  };

  const startEditEntry = (entry) => {
    if (!entry?.id) return;
    setEditingId(entry.id);
    setDialogOpen(false);
    
    // Convert UTC Date back to YYYY-MM-DD for the input 
    let formattedDate = entry.date;
    if (formattedDate && formattedDate.includes('T')) {
       formattedDate = formattedDate.split('T')[0];
    }
    
    setForm({
      caseNumber: entry.caseNumber || entry.matterNumber || "",
      partyName: entry.partyName || "",
      date: formattedDate || "",
      time: entry.time || "",
      ampm: entry.ampm || "AM",
      notes: entry.notes || ""
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const getEntriesByDate = (day) => {
    return entries.filter((entry) => {
      if (!entry.date) return false;
      let entryDateStr = entry.date;
      if (entryDateStr && entryDateStr.includes('T')) {
        entryDateStr = entryDateStr.split('T')[0]; 
      }
      
      // Parse YYYY-MM-DD exactly to avoid timezone conversion bugs when rendering
      const parts = entryDateStr.split('-');
      if (parts.length !== 3) return false;
      
      const y = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10) - 1; // Month is 0-indexed in UI currentMonth
      const d = parseInt(parts[2], 10);
      
      return (
        d === day &&
        m === currentMonth &&
        y === currentYear
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
    const totalCells = Math.ceil((totalDays + firstDay) / 7) * 7;
    let dayCounter = 1;

    for (let i = 0; i < totalCells; i++) {
      if (i < firstDay || dayCounter > totalDays) {
        days.push(<div key={`empty-${i}`} className="adv-day empty"></div>);
      } else {
        const todayEntries = getEntriesByDate(dayCounter);
        const hasEntries = todayEntries.length > 0;
        const currentDay = dayCounter;

        days.push(
          <div
            key={currentDay}
            className={`adv-day ${hasEntries ? "has-entries" : ""}`}
            onClick={() => {
              if (hasEntries) {
                setDialogEntries(todayEntries);
                setDialogOpen(true);
              }
            }}
          >
            <span className="adv-day-number">{currentDay}</span>
            {hasEntries && (
              <div className="adv-entry-badge">
                {todayEntries.length} {todayEntries.length === 1 ? 'Entry' : 'Entries'}
              </div>
            )}
          </div>
        );
        dayCounter++;
      }
    }
    return days;
  };

  return (
    <>
      <div className="adv-diary-page">
        {/* Entry Form Card */}
        <div className="adv-card adv-form-card">
          <div className="adv-header">
            <span>🖋️ Diary Entry</span>
          </div>
          <form onSubmit={handleSubmit} className="adv-form">
            <div className="adv-input-group">
              <label>Case Number</label>
              <input
                type="text"
                name="caseNumber"
                placeholder="e.g. CR-2023-104"
                value={form.caseNumber}
                onChange={handleChange}
                className="adv-input"
              />
            </div>
            <div className="adv-input-group">
              <label>Party Name</label>
              <input
                type="text"
                name="partyName"
                placeholder="Client or Opposing Party"
                value={form.partyName}
                onChange={handleChange}
                className="adv-input"
                required
              />
            </div>
            <div className="adv-input-group">
              <label>Date</label>
              <input
                type="date"
                name="date"
                value={form.date}
                onChange={handleChange}
                className="adv-input"
                required
              />
            </div>
            <div className="adv-row">
              <div className="adv-input-group" style={{ flex: 2 }}>
                <label>Time</label>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <select
                    className="adv-input adv-select"
                    style={{ padding: "12px", backgroundPosition: "calc(100% - 8px) center" }}
                    value={form.time.split(':')[0] || '12'}
                    onChange={(e) => {
                      const min = form.time.split(':')[1] || '00';
                      handleChange({ target: { name: 'time', value: `${e.target.value}:${min}` } });
                    }}
                  >
                    {Array.from({ length: 12 }, (_, i) => {
                      const h = String(i + 1).padStart(2, '0');
                      return <option key={h} value={h}>{h}</option>;
                    })}
                  </select>
                  <span style={{ fontWeight: 800 }}>:</span>
                  <select
                    className="adv-input adv-select"
                    style={{ padding: "12px", backgroundPosition: "calc(100% - 8px) center" }}
                    value={form.time.split(':')[1] || '00'}
                    onChange={(e) => {
                      const hr = form.time.split(':')[0] || '12';
                      handleChange({ target: { name: 'time', value: `${hr}:${e.target.value}` } });
                    }}
                  >
                    {Array.from({ length: 60 }, (_, i) => {
                      const m = String(i).padStart(2, '0');
                      return <option key={m} value={m}>{m}</option>;
                    })}
                  </select>
                </div>
              </div>
              <div className="adv-input-group" style={{ flex: 1 }}>
                <label>AM/PM</label>
                <select
                  name="ampm"
                  value={form.ampm}
                  onChange={handleChange}
                  className="adv-input adv-select"
                >
                  <option>AM</option>
                  <option>PM</option>
                </select>
              </div>
            </div>
            <div className="adv-input-group">
              <label>Notes</label>
              <textarea
                name="notes"
                placeholder="Hearing details, next steps..."
                value={form.notes}
                onChange={handleChange}
                className="adv-input"
              />
            </div>
            <button type="submit" className="adv-btn">
              {editingId ? "Update Entry" : "Save Entry"}
            </button>
          </form>
        </div>

        {/* Calendar Card */}
        <div className="adv-card adv-calendar-card">
          <div className="adv-header">
            <span>📅 Schedule</span>
            <div className="adv-toolbar">
              <select value={currentMonth} onChange={handleMonthChange} className="adv-select">
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i} value={i}>
                    {new Date(0, i).toLocaleString("default", { month: "long" })}
                  </option>
                ))}
              </select>
              <select value={currentYear} onChange={handleYearChange} className="adv-select">
                {Array.from({ length: 10 }, (_, i) => {
                  const year = today.getFullYear() - 5 + i;
                  return <option key={year} value={year}>{year}</option>;
                })}
              </select>
            </div>
          </div>

          <div className="adv-calendar">
            <div className="adv-weekdays">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                <div key={day} className="adv-weekday">{day}</div>
              ))}
            </div>
            <div className="adv-days-grid">
              {renderCalendar()}
            </div>
          </div>
        </div>
      </div>

      {/* Popups and Modals */}
      {showPopup && (
        <div className="adv-toast">
          ✓ Entry successfully saved!
        </div>
      )}

      {dialogOpen && (
        <div className="adv-overlay" onClick={() => setDialogOpen(false)}>
          <div className="adv-dialog" onClick={e => e.stopPropagation()}>
            <div className="adv-dialog-header">
              <span>Selected Entries</span>
              <button className="adv-dialog-close" onClick={() => setDialogOpen(false)}>×</button>
            </div>
            <div className="adv-dialog-content">
              {dialogEntries.map((entry, idx) => (
                <div key={entry.id || idx} className="adv-entry-card">
                  <div className="adv-entry-header">
                    <span className="adv-entry-title">{entry.partyName || "Unnamed Entry"}</span>
                    <div className="adv-entry-actions">
                      <button className="adv-btn-small adv-btn-edit" onClick={() => startEditEntry(entry)}>
                        Edit
                      </button>
                      <button className="adv-btn-small adv-btn-delete" onClick={() => deleteEntryById(entry.id)}>
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="adv-entry-detail"><strong>Case No:</strong> {entry.caseNumber || "N/A"}</div>
                  <div className="adv-entry-detail">
                    <strong>Time:</strong> {entry.time ? `${entry.time} ${entry.ampm}` : "Not specified"}
                  </div>
                  {entry.notes && (
                    <div className="adv-entry-detail" style={{ marginTop: '8px', padding: '8px', background: '#fff', borderRadius: '8px', border: '1px solid #eee' }}>
                      {entry.notes}
                    </div>
                  )}

                  {/* Render Linked Documents if they exist */}
                  {entry.linkedDocuments && entry.linkedDocuments.length > 0 && (
                     <div style={{ marginTop: '12px', padding: '12px', background: '#fffcf0', borderRadius: '8px', border: '1px dashed #ff8c00' }}>
                       <strong style={{ color: '#ff7a1a', display: 'block', marginBottom: '8px', fontSize: '0.85rem', textTransform: 'uppercase' }}>
                         Linked Documents
                       </strong>
                       {entry.linkedDocuments.map(doc => {
                         const getDocIcon = (type) => {
                           if (type === 'SUMMARY') return '📑';
                           if (type === 'TRANSLATION') return '🌐';
                           return '📄'; // Default/Draft
                         };
                         
                         const docTypeLabel = doc.type === 'SUMMARY' ? 'Summary' : doc.type === 'TRANSLATION' ? 'Translation' : 'Draft';
                         
                         return (
                           <div 
                             key={doc._id} 
                             onClick={() => setViewingDoc(doc)}
                             style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', padding: '4px 8px', borderRadius: '4px', transition: 'background 0.2s', border: '1px solid transparent' }}
                             onMouseOver={e => { e.currentTarget.style.background = 'rgba(255, 140, 0, 0.1)'; e.currentTarget.style.borderColor = 'rgba(255, 140, 0, 0.3)'; }}
                             onMouseOut={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; }}
                             title={`Open ${docTypeLabel} Document`}
                           >
                             <span style={{ fontSize: '1.1rem' }}>{getDocIcon(doc.type)}</span>
                             <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#ff7a1a', textDecoration: 'underline', flexGrow: 1 }}>{doc.title}</span>
                             <span style={{ fontSize: '0.7rem', padding: '2px 6px', background: 'rgba(255,140,0,0.1)', color: '#ff7a1a', borderRadius: '12px', fontWeight: 'bold' }}>
                               {docTypeLabel}
                             </span>
                           </div>
                         );
                       })}
                     </div>
                  )}

                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Document Viewing Modal */}
      {viewingDoc && (
        <div className="adv-overlay" onClick={() => setViewingDoc(null)} style={{ zIndex: 10001 }}>
          <div className="adv-dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', width: '90%', height: '80vh', display: 'flex', flexDirection: 'column' }}>
            <div className="adv-dialog-header" style={{ background: '#2c3e50', color: 'white' }}>
              <span>📄 Document: {viewingDoc.title}</span>
              <button className="adv-dialog-close" onClick={() => setViewingDoc(null)} style={{ color: 'white' }}>×</button>
            </div>
            <div className="adv-dialog-content" style={{ flexGrow: 1, overflowY: 'auto', background: '#f8fafc', padding: '24px' }}>
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'serif', fontSize: '1.05rem', lineHeight: '1.6', color: '#1a1a1a', background: 'white', padding: '40px 30px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', border: '1px solid #e2e8f0', margin: 0 }}>
                {viewingDoc.content}
              </pre>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AdvDiary;
