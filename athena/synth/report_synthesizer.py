# athena/synth/report_synthesizer.py
from typing import List, Dict
import datetime
import os

def synthesize_report(query: str, retrieved: List, debates: Dict) -> str:
    """
    Create a simple LaTeX report string.
    Includes external checks from Wikipedia, PubMed, and arXiv.
    """
    now = datetime.datetime.utcnow().isoformat()
    header = r"""
\documentclass{article}
\usepackage{hyperref}
\title{Athena Synthesis Report}
\date{%s}
\begin{document}
\maketitle
\section*{Query}
%s
\section*{Retrieved Context}
    """ % (now, query)

    body = ""
    for i, (id_, doc, meta) in enumerate(retrieved):
        source = meta.get("source", "unknown").replace("_", r"\_")
        snippet = (doc or "")[:800].replace("%", r"\%")
        body += f"\\subsection*{{Document {i+1} (source: {source})}}\n"
        body += snippet + "\n\n"

    body += "\\section*{Claims and Debate Summaries}\n"
    for claim, d in debates.items():
        body += "\\subsection*{Claim}\n" + claim.replace("%", r"\%") + "\n\n"
        body += "\\subsubsection*{Referee}\n" + (d.get("referee", "") or "").replace("%", r"\%") + "\n\n"
        body += "\\subsubsection*{PRO}\n" + "\n\n".join(d.get("pro", [])) + "\n\n"
        body += "\\subsubsection*{CON}\n" + "\n\n".join(d.get("con", [])) + "\n\n"

        # External validation section
        body += "\\subsubsection*{External checks}\n"

        wiki_hits = d.get("wiki", [])
        pubmed_hits = d.get("pubmed", [])
        arxiv_hits = d.get("arxiv", [])

        if wiki_hits:
            body += "\\textbf{Wikipedia:} " + str(wiki_hits).replace("%", r"\%") + "\n\n"
        if pubmed_hits:
            body += "\\textbf{PubMed:} " + str(pubmed_hits).replace("%", r"\%") + "\n\n"
        if arxiv_hits:
            body += "\\textbf{arXiv:} " + str(arxiv_hits).replace("%", r"\%") + "\n\n"

        if not (wiki_hits or pubmed_hits or arxiv_hits):
            body += "No external validation sources found.\n\n"

    footer = r"\end{document}"
    latex = header + body + footer

    os.makedirs("outputs", exist_ok=True)
    fname = f"outputs/athena_report_{int(datetime.datetime.utcnow().timestamp())}.tex"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(latex)
    return fname
