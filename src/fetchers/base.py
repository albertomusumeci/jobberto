"""
Interfaccia base per tutti i fetcher.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Job:
    job_id: str  # ID univoco dentro l'ATS (usato per dedup insieme all'azienda)
    title: str
    location: str
    url: str  # URL principale (di solito ATS)
    url_native: str = ""  # URL sul sito azienda, se diverso e disponibile


class BaseFetcher:
    """Sottoclassa questo per implementare un nuovo ATS."""

    name = "base"

    def fetch(self, slug: str) -> List[Job]:
        raise NotImplementedError
