"""
Interfaccia base per tutti i fetcher.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Job:
    job_id: str
    title: str
    location: str
    url: str
    url_native: str = ""


class BaseFetcher:
    """Sottoclassa questo per implementare un nuovo ATS."""

    name = "base"

    def fetch(self, company: dict) -> List[Job]:
        """
        Riceve l'intero dict company da companies.yaml.
        Fetcher semplici leggeranno solo company["slug"].
        Fetcher con parametri custom (Workday, Eightfold) leggeranno campi extra
        come company["workday_host"], company["eightfold_endpoint_type"], ecc.
        """
        raise NotImplementedError
