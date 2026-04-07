import React, { useState } from "react";
import html2pdf from "html2pdf.js";
import "./App.css";
import { processFile, translateFile } from "./api";

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
  const [loading, setLoading] = useState(false);

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
    try {
      const data =
        action === "translate"
          ? await translateFile(file, targetLanguage)
          : await processFile(file, action);

      // Optionally add paragraph breaks if missing, uncomment if needed
      // const formattedResult = (data.result || "No result returned.").replace(/\. /g, ".\n\n");

      setResult(data.result || "No result returned.");
    } catch (error) {
      console.error("Processing error:", error);
      setResult("An error occurred while processing.");
    } finally {
      setLoading(false);
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
          <div className="docai-output-title-row">
            <div className="docai-output-title">Output</div>
            {result ? (
              <button
                type="button"
                className="docai-download-pdf"
                onClick={downloadPDF}
              >
                Download as PDF
              </button>
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
    </div>
  );
};

export default DocAIPage;