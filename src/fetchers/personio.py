"""
Fetcher per Personio ATS (Personio stessa e altre scale-up EU che usano Personio come ATS).
Feed pubblico XML: https://{slug}.jobs.personio.com/xml


Formato XML root: <workzag-jobs> (nome storico pre-rebranding)
Nota: il feed non contiene descrizioni job (campo <jobDescriptions/> è vuoto).
"""

import logging
import xml.etree.ElementTree as ET
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class PersonioFetcher(BaseFetcher):
    name = "personio"

    def fetch(self, company: dict) -> List[Job]:
        slug = company["slug"]
        url = f"https://{slug}.jobs.personio.com/xml"
        headers = {
            "User-Agent": "Jobberto/1.0",
            "Accept": "application/xml, text/xml",
        }

        try:
            r = httpx.get(url, headers=headers, timeout=20)
            r.raise_for_status()
        except Exception as e:
            logger.warning(f"Personio fetch failed for {slug}: {e}")
            return []

        try:
            root = ET.fromstring(r.content)
        except ET.ParseError as e:
            logger.warning(f"Personio XML parse failed for {slug}: {e}")
            return []

        jobs = []
        for position in root.findall("position"):
            job_id = self._xml_text(position, "id")
            title = self._xml_text(position, "name")

            # Location: office principale + additionalOffices
            primary_office = self._xml_text(position, "office")
            secondary = []
            add_off = position.find("additionalOffices")
            if add_off is not None:
                for office in add_off.findall("office"):
                    if office.text:
                        secondary.append(office.text.strip())

            loc_parts = [primary_office] + secondary
            loc = ", ".join(p for p in loc_parts if p)

            # URL: Personio non fornisce URL diretto nell'XML, lo costruiamo
            job_url = f"https://{slug}.jobs.personio.com/job/{job_id}"

            jobs.append(
                Job(
                    job_id=str(job_id),
                    title=title,
                    location=loc,
                    url=job_url,
                    url_native="",
                )
            )
        return jobs

    @staticmethod
    def _xml_text(parent: ET.Element, tag: str) -> str:
        """Helper: estrae testo da child tag, ritorna '' se assente"""
        elem = parent.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return ""
