# templates.py
SYSTEM_BASE = (
    "You are a medical student who is learning from various different books. Answer ONLY from the provided context. "
    "If the answer isn't fully supported by the context, say 'Not covered in the book(s)'. 
    'Keep responses concise and exam-ready."
)

QA_TEMPLATE = (
    "\n\n# QUESTION\n{question}\n\n# CONTEXT\n{context}\n\n# ANSWER (with citations such as [book:page-page])\n"
)

GENERAL = (
    "\n\n# TASK\nCreate a concise study note card on the topic below with bullet points."
    "\nAdd a brief header if helpful. Include citations at the end of each bullet."
    "\nSuggested fields (use only those that fit the topic): Definition/Overview; Key concepts; Mechanism/Pathophysiology;"
    "\nClinical features/Findings; Diagnostics/Criteria; Staging/Severity; Management/Treatment; Dosing (if applicable);"
    "\nContraindications/Cautions; Complications/Adverse effects; Monitoring; Guidelines/Recommendations; High‑yield pearls."
    "\n\nConstraints: one fact per line; ≤12 words per line; prefer numbers and facts; no filler words;"
    "\n\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n\n# CARD\n"
)

# Med-notes specialized templates aligned with prioritization, compression, retrieval

DISEASE = (
    "\n\n# TASK\nProduce compact Disease Notes following this skeleton."
    "\nPillars: prioritize exam targets (definitions, ddx (differential diagnosis), first/best test, red flags); compress (≤12 words/line, symbols); retrieval-ready (write as quizable bullets)."
    "\nRules: one fact per line; no filler; use thresholds."
    "\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n"
    "\n# DISEASE NOTES\n"
    "Definition:\n"
    "Epidemiology/Risk:\n"
    "Pathophysiology (1–3 points):\n"
    "Clinical (Sx/Signs):\n"
    "Red flags:\n"
    "Ddx (top 5) + discriminators:\n"
    "Investigations: first test | best initial | most accurate | key cut-offs:\n"
    "Severity/Scoring:\n"
    "Management: emergency → acute → chronic → lifestyle → follow-up:\n"
    "Complications/Prognosis:\n"
    "Pearls/Pitfalls:\n"
    "5 recall Qs (question : short answer):\n"
)

DRUG = (
    "\n\n# TASK\nProduce a compact Drug Notes following this skeleton."
    "\nRules: one fact per line; ≤12 words; provide numbers/thresholds."
    "\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n"
    "\n# DRUG NOTES\n"
    "Class/MOA (Mode of Action) (1 line):\n"
    "Indications:\n"
    "Dosing quirks:\n"
    "Adverse/Contraindications:\n"
    "Monitoring:\n"
    "Interactions:\n"
    "High-yield pearl:\n"
    "5 recall Qs (question : short answer):\n"
)

PROCEDURE = (
    "\n\n# TASK\nProduce a specific Procedure's Notes following this skeleton."
    "\nRules: one fact per line; ≤12 words;"
    "\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n"
    "\n# PROCEDURE NOTES\n"
    "Indication:\n"
    "Steps (3–7 bullets):\n"
    "Complications:\n"
    "Aftercare:\n"
    "Mini-flowchart (boxes ≤4 words each):\n"
    "5 recall Qs (question : short answer):\n"
)
