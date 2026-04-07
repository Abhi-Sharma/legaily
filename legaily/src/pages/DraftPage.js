import React, { useState, useEffect } from 'react';
import html2pdf from 'html2pdf.js';
import './DraftPage.css';

const templates = [
  'Legal Notice',
  'Bail Application',
  'Affidavit',
  'Contract',
  'PIL (Public Interest Litigation)'
];

const fieldMap = {
  'Legal Notice': ['partyName', 'location', 'caseDetails'],
  'Bail Application': ['partyName', 'location', 'caseDetails', 'date'],
  'Affidavit': ['partyName', 'location', 'caseDetails', 'date'],
  'Contract': ['partyName', 'otherParty', 'location', 'caseDetails', 'date'],
  'PIL (Public Interest Litigation)': ['partyName', 'location', 'caseDetails', 'date']
};

const templateTextMap = {
  'Legal Notice': `
LEGAL NOTICE

Date: [date]

To,
[partyName]
[location]

Subject: Legal Notice for [caseDetails]

Sir/Madam,

Under instructions from and on behalf of my client, I hereby serve upon you the following legal notice:

1. That my client is a law-abiding citizen and is engaged in lawful activities.
2. That on / around __________ (date), you have __________ (acts of the opposite party) which has caused loss / injury to my client.
3. That your above acts are illegal, arbitrary, and in violation of applicable laws.
4. That despite repeated requests, you have failed to rectify the issue / comply with lawful demands.

Therefore, you are hereby called upon to:

- __________ (mention demands clearly)
- Comply within ___ days from receipt of this notice

Failing which, my client shall be constrained to initiate appropriate legal proceedings at your risk, cost, and consequences.

Advocate
[partyName]
`,
  'Bail Application': `
IN THE COURT OF __________

BAIL APPLICATION NO. ____ OF 20__

IN THE MATTER OF:

[partyName]
...Applicant

VERSUS

State of [location]
...Respondent

APPLICATION UNDER SECTION ____ CrPC FOR GRANT OF BAIL

MOST RESPECTFULLY SHOWETH:

1. That the applicant has been falsely implicated in the present case.
2. That the applicant is innocent and has committed no offence.
3. That the investigation is in progress / complete and the applicant is cooperating.
4. That the applicant is not a flight risk and undertakes to appear as and when required.
5. That no purpose will be served by further detention.

Case / FIR details (as provided):
[caseDetails]

PRAYER:

It is therefore most respectfully prayed that this Hon’ble Court may kindly grant bail to the applicant in the interest of justice.

AND FOR THIS ACT OF KINDNESS, THE APPLICANT SHALL EVER PRAY.

Place: [location]
Date: [date]

[Signature]
Advocate / Applicant
`,
  'Affidavit': `
AFFIDAVIT

I, [partyName], S/o / D/o __________, aged __ years, residing at [location], do hereby solemnly affirm and state:

1. That I am the deponent herein.
2. That I am fully aware of the facts of this affidavit.
3. That the statements made herein are true and correct to my knowledge and belief.
4. That nothing material has been concealed.

DEPONENT

VERIFICATION:

Verified at [location] on this [date] day of __________ 20__ that the contents are true and correct.

DEPONENT
`,
  'Contract': `
AGREEMENT

This Agreement is made on this [date] between:

[partyName], residing at [location] (hereinafter referred to as "First Party")

AND

[otherParty], residing at __________ (hereinafter referred to as "Second Party")

WHEREAS:

- The First Party agrees to [caseDetails]
- The Second Party agrees to __________

TERMS & CONDITIONS:

1. That the agreement shall be valid for ___ duration.
2. That consideration amount is Rs. ________.
3. That both parties agree to fulfill obligations in good faith.
4. That any dispute shall be subject to jurisdiction of __________ courts.

IN WITNESS WHEREOF both parties have signed this agreement.

First Party Signature: __________
Second Party Signature: __________
`,
  'PIL (Public Interest Litigation)': `
IN THE HON’BLE HIGH COURT OF __________

WRIT PETITION (PIL) NO. ___ OF 20__

IN THE MATTER OF:

[partyName]
...Petitioner

VERSUS

State of [location] & Others
...Respondents

PUBLIC INTEREST LITIGATION UNDER ARTICLE 226 OF THE CONSTITUTION

MOST RESPECTFULLY SHOWETH:

1. That the present petition is filed in public interest.
2. That the issue concerns [caseDetails] affecting the public at large.
3. That the respondents have failed to perform their duties.
4. That no alternative remedy is available.

PRAYER:

It is therefore prayed that this Hon’ble Court may kindly:

- Issue appropriate writ/order/direction
- Grant any other relief deemed fit

Place: [location]
Date: [date]

[Signature]
Petitioner
`
};

const Drafts = () => {
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [formData, setFormData] = useState({
    partyName: '',
    location: '',
    otherParty: '',
    caseDetails: '',
    date: ''
  });
  const [draftOutput, setDraftOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const initialFormState = {
    partyName: '',
    location: '',
    otherParty: '',
    caseDetails: '',
    date: ''
  };

  const handleTemplateChange = (e) => {
    const nextTemplate = e.target.value;
    setSelectedTemplate(nextTemplate);
    setDraftOutput('');
    setIsLoading(false);
    setFormData(initialFormState);
  };

  const handleGenerateDraft = () => {
    setIsLoading(true);

    setTimeout(() => {
      const filledTemplate = (templateTextMap[selectedTemplate] || '[Template not available]')
        .replaceAll('[partyName]', formData.partyName.trim())
        .replaceAll('[location]', formData.location.trim())
        .replaceAll('[otherParty]', formData.otherParty.trim())
        .replaceAll('[caseDetails]', formData.caseDetails.trim())
        .replaceAll('[date]', formData.date);

      setDraftOutput(filledTemplate.trim());
      setIsLoading(false);
    }, 1000);
  };

  useEffect(() => {
    if (!isLoading && draftOutput) {
      window.scrollTo(0, 0);
    }
  }, [isLoading, draftOutput]);

  const downloadPDF = () => {
    const element = document.getElementById('draftPreview');
    html2pdf().set({
      margin: 1,
      filename: `${selectedTemplate.replace(/\s+/g, '_')}_Draft.pdf`,
      html2canvas: { scale: 2 },
      jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    }).from(element).save();
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(draftOutput || '');
    } catch {
      // no-op (clipboard can fail on insecure contexts)
    }
  };

  const renderInput = (field) => {
    const labels = {
      partyName: "Party Name",
      location: "Location",
      otherParty: "Other Party",
      caseDetails: "Case Details",
      date: "Date"
    };

    return (
      <div className="form-group" key={field}>
        <label>{labels[field]}</label>
        {field === 'caseDetails' ? (
          <textarea
            rows={6}
            value={formData[field]}
            onChange={(e) => setFormData({ ...formData, [field]: e.target.value })}
            placeholder={`Enter ${labels[field]}`}
          />
        ) : (
          <input
            type={field === 'date' ? 'date' : 'text'}
            value={formData[field]}
            onChange={(e) => setFormData({ ...formData, [field]: e.target.value })}
            placeholder={`Enter ${labels[field]}`}
          />
        )}
      </div>
    );
  };

  return (
    <div className="drafts-container">
      {isLoading && (
        <div className="full-screen-overlay">
          <div className="spinner"></div>
        </div>
      )}

      <h1>📄 Legal Draft Generator</h1>

      <div className="form-group">
        <label>Select Template</label>
        <select value={selectedTemplate} onChange={handleTemplateChange}>
          <option value="">-- Choose Template --</option>
          {templates.map((template, idx) => (
            <option key={idx} value={template}>{template}</option>
          ))}
        </select>
      </div>

      {selectedTemplate && (
        <div className="form-section">
          {fieldMap[selectedTemplate].map(renderInput)}
        </div>
      )}

      <button className="generate-btn" onClick={handleGenerateDraft} disabled={!selectedTemplate}>
        Generate Draft
      </button>

      {draftOutput && (
        <>
          <div id="draftPreview" className="draft-template-page">
            <div className="draft-template-topbar">
              <div className="draft-template-date">
                {new Date().toLocaleString()}
              </div>
              <div className="draft-template-title">Court Draft Templates</div>
              <div className="draft-template-spacer" />
            </div>

            <div className="draft-template-section-title">
              <span className="draft-template-section-icon" aria-hidden="true">📄</span>
              <span className="draft-template-section-number">1.</span>
              <span className="draft-template-section-name">{selectedTemplate} Template</span>
            </div>

            <div className="draft-template-card">
              <div className="draft-template-card-header">
                <span className="draft-template-card-header-left">Writing</span>
                <button
                  type="button"
                  className="draft-template-copy-btn"
                  onClick={copyToClipboard}
                  title="Copy"
                >
                  ⧉
                </button>
              </div>
              <pre className="draft-template-content">{draftOutput}</pre>
            </div>
          </div>

          <button className="download-btn" onClick={downloadPDF}>Download as PDF</button>
        </>
      )}
    </div>
  );
};

export default Drafts;
