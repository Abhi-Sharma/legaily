import React, { useState } from "react";
import "./App.css";
import { processFile, translateFile } from "./api";

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
          <div className="docai-output-title">Output</div>
          <div className="docai-output-content white-space-pre-wrap">
            {result ? result : <span>No output yet.</span>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocAIPage;