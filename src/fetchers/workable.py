"""
Fetcher per Workable (Hugging Face).
API pubblica: https://apply.workable.com/api/v3/accounts/{slug}/jobs
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class WorkableFetcher(BaseFetcher):
    name = "workable"

    def fetch(self, company: dict) -> List[Job]:
        slug = company["slug"]
        url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
        headers = {
            "User-Agent": "Jobberto/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        all_results = []
        limit = 100
        page_token = None
        max_pages = 10

        # Workable v3 accetta POST con paginazione via "token"
        for _ in range(max_pages):
            payload = {"limit": limit}
            if page_token:
                payload["token"] = page_token

            try:
                r = httpx.post(url, json=payload, headers=headers, timeout=20)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                logger.warning(f"Workable fetch failed for {slug}: {e}")
                break

            results = data.get("results", [])
            if not results:
                break
            all_results.extend(results)

            page_token = data.get("nextPage")
            if not page_token:
                break

        jobs = []
        for j in all_results:
            job_id = str(j.get("id", "") or j.get("shortcode", ""))
            title = j.get("title", "")
            # Location: Workable ha sia location object che campo locations lista
            loc = ""
            loc_obj = j.get("location", {}) or {}
            if isinstance(loc_obj, dict):
                loc_parts = [
                    loc_obj.get("city", ""),
                    loc_obj.get("region", ""),
                    loc_obj.get("country", ""),
                ]
                loc = ", ".join(p for p in loc_parts if p)
            elif isinstance(loc_obj, str):
                loc = loc_obj

            # Fallback su locations[] se presente
            if not loc and isinstance(j.get("locations"), list) and j["locations"]:
                first = j["locations"][0]
                if isinstance(first, dict):
                    loc = first.get("city", "") or first.get("country", "")

            shortcode = j.get("shortcode", job_id)
            job_url = (
                j.get("url") or f"https://apply.workable.com/{slug}/j/{shortcode}/"
            )

            jobs.append(
                Job(
                    job_id=job_id,
                    title=title,
                    location=loc,
                    url=job_url,
                    url_native="",
                )
            )
        return jobs
