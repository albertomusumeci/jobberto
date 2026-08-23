"""
Fetcher per SmartRecruiters (Canva, Booking.com, Ubisoft, Adevinta, Delivery Hero).
API: https://api.smartrecruiters.com/v1/companies/{slug}/postings

URL pubblico: https://jobs.smartrecruiters.com/{slug}/{id}-{title-kebab-case}

Nota: NON usiamo applyUrl dell'API perché punta all'endpoint API stesso,
non alla pagina pubblica del job. Costruiamo l'URL manualmente.
"""

import logging
import re
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class SmartRecruitersFetcher(BaseFetcher):
    name = "smartrecruiters"

    def fetch(self, company: dict) -> List[Job]:
        slug = company["slug"]
        base_url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        headers = {"User-Agent": "Jobberto/1.0", "Accept": "application/json"}

        all_items = []
        offset = 0
        limit = 100
        max_pages = 20  # safety: 2000 job max

        for _ in range(max_pages):
            params = {"limit": limit, "offset": offset}
            try:
                r = httpx.get(base_url, params=params, headers=headers, timeout=20)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                logger.warning(
                    f"SmartRecruiters fetch failed for {slug} at offset {offset}: {e}"
                )
                break

            content = data.get("content", [])
            if not content:
                break
            all_items.extend(content)

            total = data.get("totalFound", 0)
            offset += limit
            if offset >= total:
                break

        jobs = []
        for j in all_items:
            job_id = str(j.get("id", ""))
            title = j.get("name", "")

            loc_obj = j.get("location", {}) or {}
            loc_parts = [
                loc_obj.get("city", ""),
                loc_obj.get("region", ""),
                loc_obj.get("country", ""),
            ]
            loc = ", ".join(p for p in loc_parts if p)

            # URL pubblico: costruito manualmente nel formato SmartRecruiters standard
            title_slug = self._slugify(title)
            url_job = f"https://jobs.smartrecruiters.com/{slug}/{job_id}-{title_slug}"

            jobs.append(
                Job(
                    job_id=job_id,
                    title=title,
                    location=loc,
                    url=url_job,
                    url_native="",
                )
            )
        return jobs

    @staticmethod
    def _slugify(text: str) -> str:
        """
        'Product Data Scientist (They/She/He)' → 'product-data-scientist-they-she-he-'
        Replica il pattern kebab-case di SmartRecruiters (mantiene trattini finali).
        """
        if not text:
            return ""
        s = text.lower()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        s = s.lstrip("-")
        return s
