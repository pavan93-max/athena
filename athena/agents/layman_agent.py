from athena.agents.debate_engine import call_llm
from athena.ingestion.pdf_ingest import extract_pdf_text


def summarize_layman_from_pdf(path: str) -> str:
    pages = extract_pdf_text(path)
    text = "\n".join([p["text"] for p in pages])

    prompt = (
        "You are summarizing a research paper. Rewrite the key points in **layman's terms**, "
        "but keep it focused strictly on the **content of the paper**. "
        "Avoid general science explanations that are not in the text. "
        "Summarize clearly:\n"
        "- What problem/question does the paper address?\n"
        "- What method/approach is used?\n"
        "- What are the key findings?\n"
        "- Why do these results matter?\n\n"
        f"Paper content:\n{text[:3000]}"  
    )
    return call_llm(prompt)


def summarize_layman_from_text(text: str) -> str:
    prompt = (
        "The following is an academic discussion (claims, debates, or conclusions). "
        "Summarize it in **layman's terms** so that a non-expert can understand, "
        "but keep it tied to the **topic of the paper**. "
        "Clearly explain:\n"
        "- What is being argued or analyzed\n"
        "- The different perspectives or evidence\n"
        "- The final takeaway in simple words\n\n"
        f"Content:\n{text[:3000]}"
    )
    return call_llm(prompt)
