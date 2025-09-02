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
    "\n\nConstraints: one fact per line; ≤12 words per line; prefer symbols (↑ ↓ → ⟂ ∴ ∆ ⇥) and numbers; no filler words; cite like [book:page-page]."
    "\n\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n\n# CARD\n"
)

# Med-notes specialized templates aligned with prioritization, compression, retrieval

DISEASE_1PAGER = (
    "\n\n# TASK\nProduce a compact Disease 1-pager following this skeleton."
    "\nPillars: prioritize exam targets (definitions, ddx, first/best test, red flags); compress (≤12 words/line, symbols); retrieval-ready (write as quizable bullets)."
    "\nRules: one fact per line; no filler; use thresholds; each bullet ends with citation [book:page-page]."
    "\nSymbols: ↑ ↓ → ⟂ ∴ ∆ ⇥.\n"
    "\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n"
    "\n# DISEASE 1-PAGER\n"
    "Definition:\n"
    "Epidemiology/Risk:\n"
    "Pathophys (1–3 arrows):\n"
    "Clinical (Sx/Signs):\n"
    "Red flags:\n"
    "Ddx (top 5) + discriminators:\n"
    "Investigations: first test | best initial | most accurate | key cut-offs:\n"
    "Severity/Scoring:\n"
    "Management: emergency → acute → chronic → lifestyle → follow-up:\n"
    "Complications/Prognosis:\n"
    "Pearls/Pitfalls:\n"
    "5 recall Qs (question : short answer):\n"
    "\n# CAN MISSED? checklist (ensure coverage)\nClinical features | Aetiology/Risk | Next step tests | Management ladder | Indications/Contra | Severity/Scoring | Similar conditions | Exam pearls | Dangers/Follow-up\n"
)

DRUG_CARD = (
    "\n\n# TASK\nProduce a compact Drug Card (half-page)."
    "\nRules: one fact per line; ≤12 words; use symbols; numbers/thresholds; each bullet has citation [book:page-page]."
    "\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n"
    "\n# DRUG CARD\n"
    "Class/MOA (1 line):\n"
    "Indications:\n"
    "Dosing quirks:\n"
    "Adverse/Contra:\n"
    "Monitoring:\n"
    "Interactions:\n"
    "High-yield pearl:\n"
    "5 recall Qs (question : short answer):\n"
)

PROCEDURE = (
    "\n\n# TASK\nProduce a Procedure cheat. Keep steps compressible and quizable."
    "\nRules: one fact per line; ≤12 words; symbols; cite each bullet."
    "\n# TOPIC\n{topic}\n\n# CONTEXT\n{context}\n"
    "\n# PROCEDURE\n"
    "Indication:\n"
    "Steps (3–7 bullets):\n"
    "Complications:\n"
    "Aftercare:\n"
    "Mini-flowchart (boxes ≤4 words each):\n"
    "5 recall Qs (question : short answer):\n"
)
