# templates.py
SYSTEM_BASE = (
    "You are a careful medical assistant. Answer ONLY from the provided context. "
    "If the answer isn't fully supported by the context, say 'Not covered in the book(s)'. "
    "Cite each claim with [book_id:page_start-page_end]. Keep responses concise and exam-ready."
)

QA_TEMPLATE = (
    "\n\n# QUESTION\n{question}\n\n# CONTEXT\n{context}\n\n# ANSWER (with citations)\n"
)

NOTE_CARD = (
    "\n\n# TASK\nCreate a concise study note card on the topic below with bullet points."
    "\nAdd a brief header if helpful. Include citations at the end of each bullet."
    "\nSuggested fields (use only those that fit the topic): Definition/Overview; Key concepts; Mechanism/Pathophysiology;"
    "\nClinical features/Findings; Diagnostics/Criteria; Staging/Severity; Management/Treatment; Dosing (if applicable);"
    "\nContraindications/Cautions; Complications/Adverse effects; Monitoring; Guidelines/Recommendations; High‑yield pearls."
    "\n\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n\n# CARD\n"
)
