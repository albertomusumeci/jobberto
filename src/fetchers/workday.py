"""
Fetcher generico per Workday.
Legge workday_host e workday_site direttamente dal companies.yaml.


Esempio YAML:
  - name: NVIDIA
    ats: workday
    slug: nvidia
    workday_host: nvidia.wd5.myworkdayjobs.com
    workday_site: NVIDIAExternalCareerSite


Il campo workday_host può essere:
- Nome host completo: "nvidia.wd5.myworkdayjobs.com"
- Solo suffisso wd: "wd5" (il fetcher costruisce host = "{slug}.wd5.myworkdayjobs.com")
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class WorkdayFetcher(BaseFetcher):
    name = "workday"

    def fetch(self, company: dict) -> List[Job]:
        slug = company["slug"]
        host_raw = company.get("workday_host", "")
        site = company.get("workday_site", "External")

        if not host_raw:
            logger.warning(f"Workday: workday_host mancante per {company.get('name')}")
            return []

        # Normalizza host: supporta sia "wd5" che "nvidia.wd5.myworkdayjobs.com"
        if host_raw.startswith("wd") and "." not in host_raw:
            # Solo suffisso wd → costruisci full host usando slug
            host = f"{slug}.{host_raw}.myworkdayjobs.com"
        else:
            host = host_raw

        url = f"https://{host}/wday/cxs/{slug}/{site}/jobs"
        headers = {
            "User-Agent": "Jobberto/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        all_postings = []
        limit = 20
        offset = 0
        max_pages = 25  # safety: 500 job max

        for _ in range(max_pages):
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "",
            }
            try:
                r = httpx.post(url, json=payload, headers=headers, timeout=15)
                if r.status_code != 200:
                    logger.warning(
                        f"Workday {company.get('name')} status {r.status_code} "
                        f"url={url} offset={offset}"
                    )
                    break
                data = r.json()
            except Exception as e:
                logger.warning(f"Workday {company.get('name')} error: {e}")
                break

            postings = data.get("jobPostings", [])
            if not postings:
                break
            all_postings.extend(postings)

            total = data.get("total", 0)
            offset += limit
            if offset >= total:
                break

        jobs = []
        for p in all_postings:
            ext_path = p.get("externalPath", "")
            job_url = f"https://{host}/en-US/{site}{ext_path}"
            jobs.append(
                Job(
                    job_id=ext_path,
                    title=p.get("title", ""),
                    location=p.get("locationsText", "") or "",
                    url=job_url,
                    url_native="",
                )
            )
        return jobs
