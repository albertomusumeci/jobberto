"""
Fetcher per Ashby (Cohere, Scale AI, Runway, ElevenLabs, ecc.)
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class AshbyFetcher(BaseFetcher):
    name = "ashby"

    def fetch(self, slug: str) -> List[Job]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        headers = {"User-Agent": "Jobberto/1.0"}
        r = httpx.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        jobs = []
        for j in data.get("jobs", []):
            jobs.append(
                Job(
                    job_id=str(j.get("id", "")),
                    title=j.get("title", ""),
                    location=j.get("location", "") or "",
                    url=j.get("jobUrl", "") or j.get("applyUrl", ""),
                    url_native="",
                )
            )
        return jobs
