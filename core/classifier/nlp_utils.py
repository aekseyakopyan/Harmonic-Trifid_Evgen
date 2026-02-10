import re
from typing import List

def clean_text(text: str) -> str:
    """Basic text cleaning."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def extract_keywords(text: str) -> List[str]:
    """Simple keyword extraction."""
    cleaned = clean_text(text)
    # Filter common stop words (simplified list)
    stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'как', 'а', 'от', 'до'}
    words = [w for w in cleaned.split() if w not in stop_words and len(w) > 2]
    return words
