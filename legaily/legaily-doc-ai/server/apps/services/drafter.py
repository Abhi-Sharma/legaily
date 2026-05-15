import os
import cohere
from typing import Dict, Any

# Templates based on PRD (INDIAN LEGAL FORMAT)
TEMPLATES = {
    "Bail Application": """{court_name}

BAIL APPLICATION

Applicant: {applicant_name}
Case Number: {case_number}

MOST RESPECTFULLY SUBMITTED:

1. That the applicant has been falsely implicated in the present case.
2. That the alleged offence falls under Section {ipc_section} of IPC.
3. That the applicant is innocent and has no criminal background.
4. That the applicant undertakes to cooperate with the investigation.

PRAYER:

It is therefore most respectfully prayed that this Hon’ble Court may kindly grant bail to the applicant.

Date: {date}
Place: {place}

Signature of Applicant""",

    "Legal Notice": """LEGAL NOTICE

To,
{recipient_name}
{recipient_address}

Subject: Legal Notice under Section {ipc_section} IPC

Sir/Madam,

Under instructions from my client, I hereby serve upon you the following legal notice:

1. That you have committed {offence_details}
2. That this act has caused {damage_details}

You are hereby called upon to rectify the issue within {time_limit} days, failing which legal action will be initiated.

Date: {date}
Place: {place}

Advocate Signature""",

    "Affidavit": """AFFIDAVIT

I, {deponent_name}, do hereby solemnly affirm:

1. That I am the deponent in this case.
2. That the facts stated are true to my knowledge.

Verified at {place} on this day of {date}.

Signature""",

    "Contract": """AGREEMENT

This Agreement is made on this day of {date} between:

Party A: {party_a_name}
Party B: {party_b_name}

TERMS AND CONDITIONS:

1. Both parties agree to {agreement_terms}
2. Payment terms {payment_terms}

Signed by both parties.

Signature A:
Signature B:""",

    "PIL": """{court_name}

PUBLIC INTEREST LITIGATION

Petitioner: {petitioner_name}

MOST RESPECTFULLY SUBMITTED:

1. That this petition is filed in public interest.
2. That the issue affects a large section of society.
3. Topic of Concern: {concern_details}

PRAYER:

The petitioner prays that this Hon’ble Court may kindly take necessary action.

Date: {date}
Place: {place}

Signature"""
}

def generate_draft(template_id: str, data: Dict[str, Any], refine_tone: bool = False) -> str:
    """
    Generates a legal draft based on a template and user data.
    Optionally refines the tone using Cohere AI.
    """
    template = TEMPLATES.get(template_id)
    if not template:
        return f"Error: Template '{template_id}' not found."

    try:
        # Step 1: Basic Template Filling
        draft = template.format(**data)

        # Step 2: Optional Tone Refinement using Cohere
        if refine_tone:
            refined_draft = refine_legal_tone(draft)
            return refined_draft

        return draft
    except KeyError as e:
        return f"Error: Missing field {str(e)} in input data."
    except Exception as e:
        return f"Error: {str(e)}"

def refine_legal_tone(text: str) -> str:
    """
    Uses Cohere to polish the drafting tone to be more formal and court-ready.
    """
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        return text + "\n\n(Note: Tone refinement skipped - COHERE_API_KEY not set)"

    try:
        co = cohere.ClientV2(api_key=api_key)
        model = os.getenv("COHERE_CHAT_MODEL", "command-r-plus")

        prompt = f"""You are a professional Indian High Court lawyer. 
Refine the following legal draft to ensure it has a strict, formal, and court-ready tone. 

CRITICAL INSTRUCTIONS:
1. Keep the COURT HEADING (the first line) and all NAMES/DETAILS exactly as they are. 
2. Do not add "IN THE COURT OF" if the document is already addressed to a "HIGH COURT".
3. Only improve the vocabulary and phrasing of the internal paragraphs and the "MOST RESPECTFULLY SUBMITTED" section.
4. Keep the overall structure (headings, sections, prayer) exactly the same.

Draft to refine:
---
{text}
---
REFINED DRAFT:"""

        response = co.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )

        if response.message and response.message.content:
            return response.message.content[0].text
        return text
    except Exception as e:
        print(f"Error refining tone: {e}")
        return text
