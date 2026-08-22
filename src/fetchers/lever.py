"""
Fetcher per Lever (Netflix, Spotify, Canva, Mistral, Perplexity, ecc.)
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class LeverFetcher(BaseFetcher):
    name = "lever"

    def fetch(self, slug: str) -> List[Job]:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        headers = {"User-Agent": "Jobberto/1.0"}
        r = httpx.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        jobs = []
        for j in data:
            loc = ""
            cat = j.get("categories") or {}
            if cat.get("location"):
                loc = cat["location"]
            elif cat.get("allLocations"):
                loc = ", ".join(cat["allLocations"])

            jobs.append(
                Job(
                    job_id=str(j.get("id", "")),
                    title=j.get("text", ""),
                    location=loc,
                    url=j.get("hostedUrl", "") or j.get("applyUrl", ""),
                    url_native="",
                )
            )
        return jobs
