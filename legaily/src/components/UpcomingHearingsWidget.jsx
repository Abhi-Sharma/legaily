import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const DIARY_API_URL = "http://localhost:5001/api/diary";

const getStatusColor = (dateString, timeString, ampm) => {
  const hearingDate = new Date(dateString);
  const now = new Date();
  
  // Set the time of hearingDate appropriately if we wanted exact hours, 
  // but day-level compares are easier for colors.
  hearingDate.setHours(0,0,0,0);
  const today = new Date();
  today.setHours(0,0,0,0);

  const diffTime = hearingDate - today;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return '#9ca3af'; // Grey - Completed/Past
  if (diffDays === 0) return '#ef4444'; // Red - Today
  return '#f59e0b'; // Yellow/Orange - Upcoming
};

export default function UpcomingHearingsWidget() {
  const [hearings, setHearings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const fetchUpcoming = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const res = await axios.get(`${DIARY_API_URL}/all`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      const allEntries = res.data || [];
      const today = new Date();
      today.setHours(0,0,0,0);
      
      const nextWeek = new Date();
      nextWeek.setDate(today.getDate() + 7);
      nextWeek.setHours(23,59,59,999);

      // Filter next 7 days
      const upcoming = allEntries.filter(entry => {
        if (!entry.date) return false;
        const entryDate = new Date(entry.date);
        return entryDate >= today && entryDate <= nextWeek;
      });

      // Sort by chronologial order
      upcoming.sort((a,b) => new Date(a.date) - new Date(b.date));
      
      setHearings(upcoming);
    } catch (error) {
      console.error("Failed to fetch upcoming hearings widget data", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUpcoming();
  }, []);

  if (isLoading) return null; // Or a skeleton loader
  
  if (hearings.length === 0) {
    return (
      <div style={widgetStyle} className="upcoming-widget">
        <div style={headerStyle}>
          <span>🗓️ Next 7 Days</span>
        </div>
        <div style={{ padding: '32px 20px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
          <div style={{ fontSize: '2.5rem', opacity: 0.8, marginBottom: '4px' }}>📭</div>
          <p style={{ margin: 0, color: '#4b5563', fontSize: '1rem', fontWeight: 600 }}>Your week is clear!</p>
          <p style={{ margin: 0, color: '#9ca3af', fontSize: '0.85rem' }}>No upcoming hearings scheduled.</p>
          
          <button 
            onClick={() => navigate('/advdiary')}
            style={{
              marginTop: '16px',
              padding: '8px 16px',
              background: 'rgba(255, 140, 0, 0.1)',
              color: '#ff7a1a',
              border: '1px solid rgba(255, 140, 0, 0.2)',
              borderRadius: '20px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onMouseOver={(e) => e.target.style.background = 'rgba(255, 140, 0, 0.15)'}
            onMouseOut={(e) => e.target.style.background = 'rgba(255, 140, 0, 0.1)'}
          >
            + Schedule Case
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={widgetStyle} className="upcoming-widget">
      <div style={headerStyle}>
        <span>🗓️ Next 7 Days</span>
        <span style={{ fontSize: '0.8rem', background: '#ffe4cc', padding: '2px 8px', borderRadius: '12px', color: '#ff7a1a' }}>
          {hearings.length} Cases
        </span>
      </div>
      <div style={listStyle}>
        {hearings.map(h => {
          const color = getStatusColor(h.date, h.time, h.ampm);
          const hasDocs = h.linkedDocuments && h.linkedDocuments.length > 0;
          return (
            <div 
              key={h._id} 
              style={{...itemStyle, borderLeft: `4px solid ${color}`}}
              onClick={() => navigate('/advdiary')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <strong style={{ fontSize: '0.95rem', color: '#1f2937', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {h.partyName}
                </strong>
                {color === '#ef4444' && <span style={{ fontSize: '0.7rem', color: '#ef4444', fontWeight: 'bold' }}>TODAY</span>}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#4b5563', marginBottom: '4px' }}>
                {h.caseNumber && `Case: ${h.caseNumber}`}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                  {new Date(h.date).toLocaleDateString()} {h.time ? `@ ${h.time} ${h.ampm}` : ''}
                </div>
                {hasDocs && <span title="Linked Documents" style={{ fontSize: '0.9rem' }}>📎</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const widgetStyle = {
  position: 'fixed',
  right: '24px',
  top: '80px', // Below the navbar
  width: '300px',
  maxHeight: 'calc(100vh - 100px)',
  background: 'rgba(255, 255, 255, 0.95)',
  backdropFilter: 'blur(10px)',
  border: '1px solid #ffcc99',
  borderRadius: '16px',
  boxShadow: '0 10px 25px rgba(255, 122, 26, 0.1)',
  display: 'flex',
  flexDirection: 'column',
  zIndex: 100,
  overflow: 'hidden'
};

const headerStyle = {
  padding: '16px',
  background: 'linear-gradient(135deg, #ff8c00 0%, #ff7a1a 100%)',
  color: 'white',
  fontWeight: 'bold',
  fontSize: '1.1rem',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
};

const listStyle = {
  padding: '12px',
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: '10px'
};

const itemStyle = {
  background: '#ffffff',
  border: '1px solid #f3f4f6',
  borderRadius: '8px',
  padding: '12px',
  cursor: 'pointer',
  transition: 'transform 0.2s, box-shadow 0.2s',
  boxShadow: '0 2px 4px rgba(0,0,0,0.02)',
};
// Use a global style to handle hover state for .upcoming-widget > div > div since it's inline
