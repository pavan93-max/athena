# athena/preprocessing/ocr_utils.py
# Optional OCR utilities. Placeholder for integrating Nougat or Tesseract.
from typing import List, Dict

def detect_equations_from_image(image_path: str) -> List[str]:
    """
    Placeholder: call to external vision model (LLaVA/CLIP/Nougat) or math OCR.
    Returns detected latex strings (if any).
    """
    # For prototype, return empty list
    return []

def summarize_page_text(text: str, max_sentences: int = 6) -> str:
    # extremely simple heuristic summary (first N sentences)
    sentences = text.split('.')
    return '.'.join(sentences[:max_sentences]).strip() + ('.' if len(sentences) > max_sentences else '')
