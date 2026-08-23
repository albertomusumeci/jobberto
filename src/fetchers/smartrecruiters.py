"""
Fetcher per SmartRecruiters (Ubisoft, Booking.com, Adevinta, Delivery Hero, ecc.)
API pubblica: https://api.smartrecruiters.com/v1/companies/{slug}/postings
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class SmartRecruitersFetcher(BaseFetcher):
    name = "smartrecruiters"

    def fetch(self, slug: str) -> List[Job]:
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        params = {"limit": 100, "offset": 0}
        headers = {"User-Agent": "Jobberto/1.0", "Accept": "application/json"}
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning(f"SmartRecruiters fetch failed for {slug}: {e}")
            return []

        jobs = []
        for j in data.get("content", []):
            job_id = str(j.get("id", ""))
            title = j.get("name", "")
            loc_obj = j.get("location", {})
            loc_parts = [
                loc_obj.get("city", ""),
                loc_obj.get("region", ""),
                loc_obj.get("country", ""),
            ]
            loc = ", ".join(p for p in loc_parts if p)

            # URL del posting: usa refNumber o id
            ref = j.get("refNumber", job_id)
            url_job = f"https://jobs.smartrecruiters.com/{slug}/{ref}"

            jobs.append(
                Job(
                    job_id=job_id, title=title, location=loc, url=url_job, url_native=""
                )
            )
        return jobs
