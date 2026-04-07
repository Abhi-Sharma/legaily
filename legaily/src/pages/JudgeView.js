import React, { useState, useEffect } from "react";
import "../styles/JudgeView.css";

export default function JudgeView() {
  const [userRole, setUserRole] = useState(null);
  const [file, setFile] = useState(null);
  const [cid, setCid] = useState("");
  const [walletAddress, setWalletAddress] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState("");

  const [lawyers, setLawyers] = useState([
    { name: "Anmol", email: "anmolgupta1478@gmail.com" },
    { name: "Abhi Sharma", email: "abhisharma.rediffmail@gmail.com" },
    { name: "Aaditya Raj Joshi", email: "aadityarajj3210@gmail.com" },
    { name: "Bhavesh Khandelwal", email: "bhaveshkhandelwal1232@gmail.com" },
  ]);

  const [showDialog, setShowDialog] = useState(false);
  const [newLawyerName, setNewLawyerName] = useState("");
  const [newLawyerEmail, setNewLawyerEmail] = useState("");

  const pinataApiKey = "87ae79a4ac4567f97885";
  const pinataApiSecret = "2b72ef2516a7cc4dfc31e8ae475698011492a909ad95fe1f40dbc35f1b11fc24";
  const pinataJWT = "YOUR_PINATA_JWT";
  const useJWT = false;

  useEffect(() => {
    setUserRole(localStorage.getItem("role"));
  }, []);

  const uploadFile = async () => {
    if (!file) return alert("Please select a file");

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const options = JSON.stringify({ cidVersion: 1 });
      formData.append('pinataOptions', options);

      const response = await fetch("https://api.pinata.cloud/pinning/pinFileToIPFS", {
        method: 'POST',
        headers: useJWT
          ? { Authorization: `Bearer ${pinataJWT}` }
          : {
              'pinata_api_key': pinataApiKey,
              'pinata_secret_api_key': pinataApiSecret
            },
        body: formData
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      const newCid = data.IpfsHash;
      setCid(newCid);
      alert("Uploaded successfully! CID: " + newCid);
    } catch (error) {
      console.error("Error uploading to Pinata:", error);
      alert("Upload failed: " + error.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendEmail = () => {
    if (!selectedEmail || !cid) {
      alert("Please upload a file and select a lawyer first.");
      return;
    }

    const subject = encodeURIComponent("Legal Document CID from Judge");
    const body = encodeURIComponent(`Dear Lawyer,\n\nPlease find the IPFS CID for the legal document:\n\nCID: ${cid}\n\nRegards,\nJudge`);
    const mailtoLink = `https://mail.google.com/mail/?view=cm&fs=1&to=${selectedEmail}&su=${subject}&body=${body}`;
    window.open(mailtoLink, "_blank");
  };

  const handleAddLawyer = () => {
    if (newLawyerName && newLawyerEmail) {
      setLawyers([...lawyers, { name: newLawyerName, email: newLawyerEmail }]);
      setNewLawyerName("");
      setNewLawyerEmail("");
      setShowDialog(false);
    } else {
      alert("Please fill both name and email fields.");
    }
  };

  if (userRole !== "judge") {
    return (
      <div className="judge-container">
        <h1 style={{ color: "red", fontSize: "1.8rem", fontWeight: 700 }}>
          Not Authorized - Judges only
        </h1>
      </div>
    );
  }

  return (
    <div className="judge-container">
      <div className="judge-card">
        <div className="judge-header">
          <h1 className="judge-title">Judge Dashboard</h1>
        </div>

        <div className="judge-info">
          <p className="judge-role">Role: Judge</p>
          <p className="judge-cid">IPFS CID: {cid || "Not uploaded yet"}</p>
          <p className="judge-instructions">
            Upload legal documents securely. Use the upload button below to pin files to IPFS.
          </p>
        </div>

        <div className="judge-subtitle-container">
          <img
            src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
            alt="Judge Icon"
            className="judge-icon"
          />
        </div>

        <div className="upload-wrapper">
          <label className="upload-label">Upload Document</label>
          <div className="upload-section">
            <input
              type="file"
              onChange={(e) => setFile(e.target.files[0])}
              disabled={isUploading}
              className="upload-input"
            />
            <button
              onClick={uploadFile}
              disabled={isUploading || !file}
              className="upload-button"
            >
              {isUploading ? "Uploading..." : "Upload Now"}
            </button>
          </div>
          {file && <p className="selected-file">Selected: {file.name}</p>}
        </div>

        <div className="lawyer-select-wrapper">
          <label className="upload-label">Select Lawyer to Send CID</label>
          <select
            value={selectedEmail}
            onChange={(e) => setSelectedEmail(e.target.value)}
            className="upload-input"
          >
            <option value="">-- Select a Lawyer --</option>
            {lawyers.map((lawyer, index) => (
              <option key={index} value={lawyer.email}>
                {lawyer.name} ({lawyer.email})
              </option>
            ))}
          </select>

          <button
            onClick={handleSendEmail}
            disabled={!cid || !selectedEmail}
            className="upload-button"
            style={{ marginTop: "1rem" }}
          >
            Send CID via Gmail
          </button>

          <button
            onClick={() => setShowDialog(true)}
            className="upload-button"
            style={{ marginTop: "1rem", backgroundColor: "#444" }}
          >
            + Add Lawyer
          </button>
        </div>
      </div>

      {/* Dialog */}
      {showDialog && (
        <div className="dialog-overlay">
          <div className="dialog-box">
            <h3>Add New Lawyer</h3>
            <input
              type="text"
              placeholder="Name"
              value={newLawyerName}
              onChange={(e) => setNewLawyerName(e.target.value)}
              className="upload-input"
            />
            <input
              type="email"
              placeholder="Email"
              value={newLawyerEmail}
              onChange={(e) => setNewLawyerEmail(e.target.value)}
              className="upload-input"
            />
            <div className="dialog-buttons">
              <button onClick={handleAddLawyer} className="upload-button">
                Add
              </button>
              <button
                onClick={() => setShowDialog(false)}
                className="upload-button"
                style={{ backgroundColor: "#888" }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
