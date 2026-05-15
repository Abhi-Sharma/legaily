import React, { useState, useEffect } from 'react';
import html2pdf from 'html2pdf.js';
import axios from 'axios';
import './DraftPage.css';

const AI_BACKEND_URL = "http://localhost:8000";
const DIARY_API_URL = "http://localhost:5001/api/diary";

const templates = [
  'Bail Application',
  'Legal Notice',
  'Affidavit',
  'Contract',
  'PIL'
];

const fieldMap = {
  'Bail Application': [
    { key: 'court_name', label: 'Court Heading', type: 'text', placeholder: 'e.g. IN THE COURT OF THE DISTRICT JUDGE, DELHI' },
    { key: 'applicant_name', label: 'Applicant Name', type: 'text' },
    { key: 'case_number', label: 'Case Number', type: 'text' },
    { key: 'ipc_section', label: 'IPC Section(s)', type: 'text' },
    { key: 'date', label: 'Date', type: 'date' },
    { key: 'place', label: 'Place', type: 'text' }
  ],
  'Legal Notice': [
    { key: 'recipient_name', label: 'To (Recipient Name)', type: 'text' },
    { key: 'recipient_address', label: 'Recipient Address', type: 'textarea' },
    { key: 'ipc_section', label: 'Under Section', type: 'text' },
    { key: 'offence_details', label: 'Offence Details', type: 'textarea' },
    { key: 'damage_details', label: 'Damage/Loss Details', type: 'textarea' },
    { key: 'time_limit', label: 'Time Limit (Days)', type: 'number' },
    { key: 'date', label: 'Date', type: 'date' },
    { key: 'place', label: 'Place', type: 'text' }
  ],
  'Affidavit': [
    { key: 'deponent_name', label: 'Deponent Name', type: 'text' },
    { key: 'date', label: 'Date', type: 'date' },
    { key: 'place', label: 'Place', type: 'text' }
  ],
  'Contract': [
    { key: 'party_a_name', label: 'Party A Name', type: 'text' },
    { key: 'party_b_name', label: 'Party B Name', type: 'text' },
    { key: 'agreement_terms', label: 'Agreement Terms', type: 'textarea' },
    { key: 'payment_terms', label: 'Payment Terms', type: 'textarea' },
    { key: 'date', label: 'Date', type: 'date' }
  ],
  'PIL': [
    { key: 'court_name', label: 'Court Heading', type: 'text', placeholder: 'e.g. IN THE HIGH COURT OF KARNATAKA' },
    { key: 'petitioner_name', label: 'Petitioner Name', type: 'text' },
    { key: 'concern_details', label: 'Topic of Public Concern', type: 'textarea' },
    { key: 'date', label: 'Date', type: 'date' },
    { key: 'place', label: 'Place', type: 'text' }
  ]
};

const Drafts = () => {
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [formData, setFormData] = useState({});
  const [refineTone, setRefineTone] = useState(false);
  const [draftOutput, setDraftOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Diary linking state
  const [diaryEntries, setDiaryEntries] = useState([]);
  const [selectedEntryId, setSelectedEntryId] = useState('');
  const [isSavingToDiary, setIsSavingToDiary] = useState(false);

  useEffect(() => {
    // Page style initialization
    document.body.style.margin = '0';
    document.body.style.backgroundColor = '#fff8f0';
    
    // Fetch user's diary entries for linking
    const fetchDiaryEntries = async () => {
      const token = localStorage.getItem("token");
      if (!token) return;
      try {
        const res = await axios.get(`${DIARY_API_URL}/all`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        setDiaryEntries(res.data);
      } catch (err) {
        console.error("Failed to fetch diary entries", err);
      }
    };
    
    fetchDiaryEntries();

    return () => {
      document.body.style.backgroundColor = '';
    };
  }, []);

  const handleTemplateChange = (e) => {
    const nextTemplate = e.target.value;
    setSelectedTemplate(nextTemplate);
    setDraftOutput('');
    setFormData({});
  };

  const handleInputChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleGenerateDraft = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${AI_BACKEND_URL}/api/draft/`, {
        template_id: selectedTemplate,
        data: formData,
        refine_tone: refineTone
      });
      setDraftOutput(response.data.result);
    } catch (error) {
      console.error("Error generating draft:", error);
      alert("Failed to generate draft. Please check if the backend is running.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoading && draftOutput) {
      const element = document.getElementById('draftPreview');
      if (element) element.scrollIntoView({ behavior: 'smooth' });
    }
  }, [isLoading, draftOutput]);

  const downloadPDF = () => {
    const element = document.getElementById('draftContent');
    const opt = {
      margin: [1, 1, 1, 1.1],
      filename: `${selectedTemplate.replace(/\s+/g, '_')}_Draft.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'in', format: 'legal', orientation: 'portrait' }
    };
    html2pdf().set(opt).from(element).save();
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(draftOutput || '');
      alert("Draft copied to clipboard!");
    } catch (err) {
      console.error("Clipboard failed", err);
    }
  };

  const saveToDiary = async () => {
    if (!selectedEntryId) {
      alert("Please select a Case/Diary Entry to save this document to.");
      return;
    }
    
    const token = localStorage.getItem("token");
    if (!token) {
      alert("Please login first to save documents.");
      return;
    }

    setIsSavingToDiary(true);
    try {
      const payload = {
        title: `${selectedTemplate} - Auto Generated`,
        type: 'AI_GENERATED',
        content: draftOutput
      };

      await axios.post(`${DIARY_API_URL}/${selectedEntryId}/link-document`, payload, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      alert("Success! Document saved to your Diary Entry.");
      setSelectedEntryId(''); // reset selection
    } catch (err) {
      console.error("Failed to link document", err);
      alert("Failed to save to Diary.");
    } finally {
      setIsSavingToDiary(false);
    }
  };

  return (
    <div className="drafts-page">
      {isLoading && (
        <div className="full-screen-overlay">
          <div className="spinner-container">
            <div className="spinner"></div>
            <p>Drafting Court-Ready Document...</p>
          </div>
        </div>
      )}

      <div className="draft-container">
        <header className="draft-header-minimal">
          <h1>🧑‍⚖️ Draft Generator</h1>
        </header>

        <main className="draft-main">
          <section className="form-section">
            <div className="form-group mb-4">
              <label>Choose Document Type</label>
              <select value={selectedTemplate} onChange={handleTemplateChange}>
                <option value="">-- Select Template --</option>
                {templates.map((t, idx) => (
                  <option key={idx} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {selectedTemplate && (
              <div className="template-fields-grid">
                {fieldMap[selectedTemplate].map((field) => (
                  <div key={field.key} className={`form-group ${field.type === 'textarea' ? 'full-width' : ''}`}>
                    <label>{field.label}</label>
                    {field.type === 'textarea' ? (
                      <textarea
                        rows={5}
                        value={formData[field.key] || ''}
                        onChange={(e) => handleInputChange(field.key, e.target.value)}
                        placeholder={field.placeholder || `Provide details for ${field.label}...`}
                      />
                    ) : (
                      <input
                        type={field.type}
                        value={formData[field.key] || ''}
                        onChange={(e) => handleInputChange(field.key, e.target.value)}
                        placeholder={field.placeholder || `Enter ${field.label}`}
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            {selectedTemplate && (
              <div className="draft-actions">
                <label className="ai-toggle">
                  <input 
                    type="checkbox" 
                    checked={refineTone} 
                    onChange={(e) => setRefineTone(e.target.checked)} 
                  />
                  <span>Refine Tone (Experimental AI)</span>
                </label>
                <button 
                  className="generate-btn" 
                  onClick={handleGenerateDraft}
                  disabled={!selectedTemplate}
                >
                  Generate Professional Draft
                </button>
              </div>
            )}
          </section>

          {draftOutput && (
            <section id="draftPreview" className="preview-section">
              <div className="preview-toolbar">
                <h3>Draft Preview</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                   <select 
                     value={selectedEntryId} 
                     onChange={(e) => setSelectedEntryId(e.target.value)}
                     style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #ffcc99', fontSize: '0.9rem', outline: 'none', minWidth: '180px', color: '#333' }}
                   >
                     <option value="">-- Save to Diary Entry --</option>
                     {diaryEntries.map(entry => (
                       <option key={entry._id} value={entry._id}>
                         {entry.partyName} ({new Date(entry.date).toLocaleDateString()})
                       </option>
                     ))}
                   </select>
                   <button 
                     onClick={saveToDiary} 
                     disabled={!selectedEntryId || isSavingToDiary}
                     className="btn-primary"
                     style={{ 
                       background: selectedEntryId ? '#ff8c00' : '#ccc',
                       opacity: selectedEntryId ? 1 : 0.7,
                       boxShadow: selectedEntryId ? '0 2px 8px rgba(255, 140, 0, 0.2)' : 'none'
                     }}
                   >
                     {isSavingToDiary ? 'Saving...' : 'Link Document'}
                   </button>
                </div>

                <div className="toolbar-buttons">
                  <button onClick={copyToClipboard} className="btn-secondary">Copy Text</button>
                  <button onClick={downloadPDF} className="btn-primary">Download PDF</button>
                </div>
              </div>

              <div id="draftContent" className="legal-paper">
                <pre className="draft-body">{draftOutput}</pre>
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
};

export default Drafts;
