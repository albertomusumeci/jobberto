"""
Fetcher per Greenhouse.
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class GreenhouseFetcher(BaseFetcher):
    name = "greenhouse"

    def fetch(self, company: dict) -> List[Job]:
        slug = company["slug"]
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        headers = {"User-Agent": "Jobberto/1.0"}
        r = httpx.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        jobs = []
        for j in data.get("jobs", []):
            jobs.append(
                Job(
                    job_id=str(j["id"]),
                    title=j.get("title", ""),
                    location=(j.get("location") or {}).get("name", ""),
                    url=j.get("absolute_url", ""),
                    url_native="",
                )
            )
        return jobs
