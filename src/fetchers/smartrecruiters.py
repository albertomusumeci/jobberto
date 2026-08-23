"""
Fetcher per SmartRecruiters (Canva, Booking.com, Ubisoft, Adevinta, Delivery Hero).
API: https://api.smartrecruiters.com/v1/companies/{slug}/postings
"""

import logging
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
        max_pages = 10  # safety: 1000 job max

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

            ref = j.get("refNumber", job_id)
            url_job = f"https://jobs.smartrecruiters.com/{slug}/{ref}"

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
