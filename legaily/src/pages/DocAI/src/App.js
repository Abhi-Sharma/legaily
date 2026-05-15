import React, { useState, useRef, useEffect } from "react";
import html2pdf from "html2pdf.js";
import axios from "axios";
import "./App.css";
import { processFile, translateFile, askSummaryQuestion } from "./api";

const DIARY_API_URL = "http://localhost:5001/api/diary";

/** Turn plain API text into styled blocks: **bold**, lists, dividers. */
function parseInlineBold(text) {
  const parts = String(text).split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    const m = part.match(/^\*\*([^*]+)\*\*$/);
    if (m) return <strong key={i}>{m[1]}</strong>;
    return <span key={i}>{part}</span>;
  });
}

function renderFormattedOutput(text) {
  if (!text) return null;
  const lines = String(text).split("\n");
  return lines.map((line, idx) => {
    const key = `fmt-${idx}`;
    const trimmed = line.trim();
    if (!trimmed) {
      return <div key={key} className="docai-fmt-break" aria-hidden="true" />;
    }
    if (/^[-_=]{3,}$/.test(trimmed)) {
      return <hr key={key} className="docai-fmt-divider" />;
    }
    if (/^##\s+/.test(trimmed)) {
      return (
        <h3 key={key} className="docai-fmt-heading">
          {parseInlineBold(trimmed.replace(/^##\s+/, ""))}
        </h3>
      );
    }
    const subMatch = trimmed.match(/^\*\*([^*]+)\*\*:?\s*$/);
    if (subMatch) {
      return (
        <h4 key={key} className="docai-fmt-subheading">
          {subMatch[1]}
        </h4>
      );
    }
    const t = trimmed;
    const isNumbered = /^\d+\.\s/.test(t);
    const isBullet = /^[-•*]\s/.test(t);
    let className = "docai-fmt-para";
    if (isNumbered) className = "docai-fmt-numbered";
    else if (isBullet) className = "docai-fmt-bullet";

    const displayLine = isBullet
      ? line.trimEnd().replace(/^[\s]*[-•*]\s/, "")
      : line.trimEnd();

    return (
      <p key={key} className={className}>
        {parseInlineBold(displayLine)}
      </p>
    );
  });
}

const DocAIPage = () => {
  const [file, setFile] = useState(null);
  const [fileUrl, setFileUrl] = useState(null);
  const [action, setAction] = useState("translate");
  const [targetLanguage, setTargetLanguage] = useState("urdu");
  const [result, setResult] = useState("");
  const [fullText, setFullText] = useState("");
  const [loading, setLoading] = useState(false);
  const [qaHistory, setQaHistory] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const qaEndRef = useRef(null);

  // Diary Linking State
  const [diaryEntries, setDiaryEntries] = useState([]);
  const [selectedEntryId, setSelectedEntryId] = useState("");
  const [isSavingToDiary, setIsSavingToDiary] = useState(false);

  useEffect(() => {
    qaEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [qaHistory, asking]);

  useEffect(() => {
    // Fetch cases for diary linking
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
  }, []);

  // Handle file upload and create preview URL
  const handleFileChange = (e) => {
    const uploadedFile = e.target.files[0];

    if (uploadedFile) {
      if (uploadedFile.type !== "application/pdf") {
        alert("Please upload a valid PDF file.");
        return;
      }

      const url = URL.createObjectURL(uploadedFile);
      setFile(uploadedFile);
      setFileUrl(url);
      setResult("");
      setFullText("");
      setQaHistory([{role: 'assistant', content: 'Hello! I am ready to answer any questions you have about this document.'}]);
    }
  };

  // Submit handler for backend processing
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return alert("Please upload a file");
    if (action === "translate" && !targetLanguage) {
      return alert("Select a target language");
    }
    setLoading(true);
    setQaHistory([{role: 'assistant', content: 'Hello! I am ready to answer any questions you have about this document.'}]);
    try {
      const data =
        action === "translate"
          ? await translateFile(file, targetLanguage)
          : await processFile(file, action);

      setResult(data.result || "No result returned.");
      setFullText(data.full_text || "");
    } catch (error) {
      console.error("Processing error:", error);
      setResult("An error occurred while processing.");
    } finally {
      setLoading(false);
    }
  };

  const handleAskQuestion = async (e) => {
    e.preventDefault();
    if (!currentQuestion.trim() || !result) return;

    const question = currentQuestion.trim();
    setCurrentQuestion("");
    const updatedHistory = [...qaHistory, { role: "user", content: question }];
    setQaHistory(updatedHistory);
    setAsking(true);

    try {
      // Use fullText if available, otherwise fallback to result (summary)
      const context = fullText || result;
      const data = await askSummaryQuestion(context, question, qaHistory);
      setQaHistory((prev) => [...prev, { role: "assistant", content: data.reply || "No response." }]);
    } catch (error) {
      console.error("Q&A error:", error);
      setQaHistory((prev) => [...prev, { role: "assistant", content: "Error fetching answer." }]);
    } finally {
      setAsking(false);
    }
  };

  const downloadPDF = () => {
    const element = document.getElementById("docaiPdfPreview");
    if (!element || !result) return;

    const actionLabel =
      action === "translate"
        ? `Translate_${targetLanguage}`
        : "Summary";
    const baseName = file
      ? file.name.replace(/\.pdf$/i, "")
      : "CaseFile";
    const filename = `${baseName}_${actionLabel}.pdf`.replace(
      /[^a-zA-Z0-9._-]/g,
      "_"
    );

    html2pdf()
      .set({
        margin: 0.75,
        filename,
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: "in", format: "letter", orientation: "portrait" },
      })
      .from(element)
      .save();
  };

  const saveToDiary = async () => {
    if (!selectedEntryId) return alert("Please select a Case/Diary Entry.");
    const token = localStorage.getItem("token");
    if (!token) return alert("Please login first to save documents.");

    setIsSavingToDiary(true);
    try {
      const docType = action === "translate" ? "TRANSLATION" : "SUMMARY";
      const docTitle = action === "translate" 
        ? `${file ? file.name : 'Document'} - ${targetLanguage.charAt(0).toUpperCase() + targetLanguage.slice(1)} Translation`
        : `${file ? file.name : 'Document'} - AI Summary`;

      const payload = {
        title: docTitle,
        type: docType,
        content: result
      };

      await axios.post(`${DIARY_API_URL}/${selectedEntryId}/link-document`, payload, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      alert("Success! Document saved to your Diary Entry.");
      setSelectedEntryId("");
    } catch (err) {
      console.error("Failed to link document", err);
      alert("Failed to save to Diary.");
    } finally {
      setIsSavingToDiary(false);
    }
  };

  return (
    <div className="docai-main">
      <div className="docai-actions">
        <svg className="decorative-circles">
          <circle cx="440" cy="110" r="120" />
          <circle cx="520" cy="60" r="80" />
        </svg>

        <input
          id="file-upload"
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
        <label htmlFor="file-upload" className="docai-upload-btn">
          {file ? "Change File" : "Upload File"}
        </label>
        <span className="docai-selected-file" title={file ? file.name : ""}>
          {file ? file.name : "No file selected"}
        </span>

        <div className="docai-controls-group">
        <div className="docai-btn-group">
          {["translate", "summarize"].map((opt) => (
            <button
              key={opt}
              className={action === opt ? "active" : ""}
              onClick={() => setAction(opt)}
            >
              {opt.charAt(0).toUpperCase() + opt.slice(1)}
            </button>
          ))}
        </div>

        <div className="docai-language-wrapper">
          <select
            className="docai-language-select"
            value={action === "translate" ? targetLanguage : ""}
            onChange={(e) => setTargetLanguage(e.target.value)}
            disabled={action === "summarize"}
          >
            <option value="">
              {action === "summarize" ? "—" : "-- Select Language --"}
            </option>
            {[
              "hindi", "english", "bengali", "telugu", "marathi", "tamil",
              "urdu", "gujarati", "kannada", "malayalam", "punjabi", "odia",
              "assamese",
            ].map((lang) => (
              <option key={lang} value={lang}>
                {lang.charAt(0).toUpperCase() + lang.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <button
          className="docai-get-answer"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? "Processing..." : "Get Answer"}
        </button>
        </div>
      </div>

      <div className="docai-content">
        <div className="docai-file-viewer">
          {fileUrl ? (
            <iframe
              src={fileUrl}
              title="PDF Preview"
              width="100%"
              height="100%"
              style={{ border: "none" }}
            />
          ) : (
            <div className="docai-file-placeholder">
              <span>No file uploaded</span>
            </div>
          )}
        </div>
        <div className="docai-output-window">
          <div className="docai-output-title-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <div className="docai-output-title">Output</div>
            {result ? (
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <select 
                    value={selectedEntryId} 
                    onChange={(e) => setSelectedEntryId(e.target.value)}
                    className="docai-language-select"
                    style={{ width: '220px', minWidth: 'auto', padding: '8px 12px' }}
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
                    className="docai-get-answer"
                    style={{ 
                      minWidth: 'auto',
                      padding: '8px 16px',
                      background: selectedEntryId ? '#f47b20' : '#ccc',
                      opacity: selectedEntryId ? 1 : 0.7
                    }}
                  >
                    {isSavingToDiary ? 'Saving...' : 'Link to Case'}
                  </button>
                </div>
                
                <button
                  type="button"
                  className="docai-download-pdf"
                  onClick={downloadPDF}
                >
                  Download PDF
                </button>
              </div>
            ) : null}
          </div>
          <div className="docai-output-content">
            {!result && <span className="docai-output-empty">No output yet.</span>}
            {result && (
              <div id="docaiPdfPreview" className="docai-pdf-preview-box">
                <div className="docai-pdf-paper">
                  <div className="docai-pdf-header">
                    <div className="docai-pdf-brand">Legaily</div>
                    <div className="docai-pdf-tag">Legal AI Assistance</div>
                  </div>

                  <h2 className="docai-pdf-heading">
                    {action === "translate" ? "Case File Translation" : "Case File Summary"}
                  </h2>

                  <div className="docai-pdf-meta-row">
                    {file && <div className="docai-pdf-meta">Source: {file.name}</div>}
                    {action === "translate" && (
                      <div className="docai-pdf-meta">
                        Target: {targetLanguage.charAt(0).toUpperCase() + targetLanguage.slice(1)}
                      </div>
                    )}
                  </div>

                  <hr className="docai-pdf-rule" />

                  <div className="docai-pdf-section-heading">
                    {action === "translate" ? "Translation" : "Summary"}
                  </div>

                  <div className="docai-pdf-body docai-formatted-root">
                    {renderFormattedOutput(result)}
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>

      {action === "summarize" && result && (
        <div className="docai-qa-section">
          <div className="docai-qa-title">Ask Questions about this Document</div>
          <div className="docai-qa-history">
            {qaHistory.map((msg, idx) => (
              <div key={idx} className={`docai-qa-message ${msg.role}`}>
                {msg.role === "assistant" ? renderFormattedOutput(msg.content) : msg.content}
              </div>
            ))}
            {asking && (
              <div className="docai-qa-message assistant">
                <div className="docai-loading">
                  <div className="docai-spinner"></div>
                  <span>Thinking...</span>
                </div>
              </div>
            )}
            <div ref={qaEndRef} />
          </div>
          <form onSubmit={handleAskQuestion} className="docai-qa-input-area">
            <input
              type="text"
              className="docai-qa-input"
              placeholder="Ask a question..."
              value={currentQuestion}
              onChange={(e) => setCurrentQuestion(e.target.value)}
              disabled={asking}
            />
            <button type="submit" className="docai-qa-submit" disabled={asking || !currentQuestion.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default DocAIPage;