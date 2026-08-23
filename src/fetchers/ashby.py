"""
Fetcher per Ashby (Snowflake, Confluent, DeepL, Miro, OpenAI, ecc.)
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class AshbyFetcher(BaseFetcher):
    name = "ashby"

    def fetch(self, company: dict) -> List[Job]:
        slug = company["slug"]
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        headers = {"User-Agent": "Jobberto/1.0"}
        r = httpx.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        jobs = []
        for j in data.get("jobs", []):
            # Ashby: gestione secondary locations
            loc = j.get("location", "") or ""
            sec = j.get("secondaryLocations", [])
            if sec:
                sec_names = [s.get("location", "") for s in sec if s.get("location")]
                if sec_names:
                    loc = (
                        loc + ", " + ", ".join(sec_names)
                        if loc
                        else ", ".join(sec_names)
                    )

            jobs.append(
                Job(
                    job_id=str(j.get("id", "")),
                    title=j.get("title", ""),
                    location=loc,
                    url=j.get("jobUrl", "") or j.get("applyUrl", ""),
                    url_native="",
                )
            )
        return jobs
