"""
Normalizzazione del testo per matching robusto:
- Lowercase
- Rimozione accenti (Zürich -> zurich)
- Espansione abbreviazioni (Sr. -> senior, ML -> machine learning)
- Normalizzazione spazi e punteggiatura
"""
import re
import unicodedata


# Dizionario abbreviazioni -> forma estesa
# Applicato PRIMA del matching regex, così sia "ML Engineer" che "Machine Learning Engineer" matchano
ABBREVIATIONS = [
    # Seniority
    (r'\bsr\.?\b', 'senior'),
    (r'\bsnr\.?\b', 'senior'),
    (r'\bjr\.?\b', 'junior'),
    (r'\bjnr\.?\b', 'junior'),


    # AI/ML
    (r'\bml\b', 'machine learning ml'),
    (r'\bai\b', 'artificial intelligence ai'),
    (r'\bmle\b', 'machine learning engineer'),
    (r'\bmlops\b', 'machine learning operations mlops'),
    (r'\bnlp\b', 'natural language processing nlp'),
    (r'\bllm\b', 'large language model llm'),
    (r'\bgenai\b', 'generative ai genai'),
    (r'\brl\b', 'reinforcement learning'),
    (r'\bdl\b', 'deep learning'),


    # Software
    (r'\bswe\b', 'software engineer swe'),
    (r'\bsw\b', 'software'),
    (r'\bdev\b', 'developer'),
    (r'\beng\.?\b', 'engineer'),
    (r'\bengr\.?\b', 'engineer'),


    # Data
    (r'\bds\b', 'data scientist ds'),
    (r'\bde\b', 'data engineer de'),
    (r'\bae\b', 'analytics engineer ae'),
    (r'\bbi\b', 'business intelligence bi'),
    (r'\bbie\b', 'business intelligence engineer'),


    # Livelli
    (r'\biv\b', 'staff iv'),
    (r'\biii\b', 'senior iii'),
    (r'\bii\b', 'mid ii'),
]




def strip_accents(text: str) -> str:
    """Zürich -> Zurich, München -> Munchen, Genève -> Geneve"""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))




def normalize(text: str) -> str:
    """
    Pipeline completa di normalizzazione:
    1. rimozione accenti
    2. lowercase
    3. sostituzione separatori speciali (/ - , _) con spazi
    4. compressione spazi multipli
    5. espansione abbreviazioni
    """
    if not text:
        return ""


    text = strip_accents(text)
    text = text.lower()


    # AI/ML, ML/AI, AI-ML, AI,ML → tutti equivalenti
    text = re.sub(r'[\/\-_,]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()


    # Espansione abbreviazioni: applicata in modo che il testo
    # contenga SIA la forma corta sia quella estesa
    for pattern, expansion in ABBREVIATIONS:
        text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)


    text = re.sub(r'\s+', ' ', text).strip()
    return text




def normalize_location(text: str) -> str:
    """Normalizza località: 'Munich, Germany' -> 'munich germany'"""
    if not text:
        return ""
    text = strip_accents(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

