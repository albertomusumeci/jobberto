"""
Fetcher generico per Workday.
Attenzione: Workday richiede un endpoint per-tenant.
Questo fetcher usa una mappa configurabile; se il tenant non è mappato, ritorna [].
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


# Mappa slug → (tenant Workday, site)
# Aggiungi qui se scopri nuovi tenant. Alcuni sono soggetti a cambio nel tempo.
WORKDAY_TENANTS = {
    "nvidia": ("nvidia", "NVIDIAExternalCareerSite"),
    "servicenow": ("servicenow", "ServiceNowCareers"),
    "atlassian": ("atlassian", "External"),
    "zoom": ("zoom", "Zoom"),
    "paypal": ("paypal", "jobs"),
    "booking": ("booking", "Booking"),
    "uber": ("uber", "uberexternal"),
    "adevinta": ("adevinta", "External_Career_Site"),
}


class WorkdayFetcher(BaseFetcher):
    name = "workday"

    def fetch(self, slug: str) -> List[Job]:
        if slug not in WORKDAY_TENANTS:
            logger.warning(f"Workday tenant non mappato per slug='{slug}'. Salto.")
            return []

        tenant, site = WORKDAY_TENANTS[slug]
        url = f"https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"

        payload = {"appliedFacets": {}, "limit": 50, "offset": 0, "searchText": ""}
        headers = {
            "User-Agent": "Jobberto/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Alcuni tenant sono su wd1/wd3/wd5. Provo wd5 poi wd3 poi wd1.
        for wd in ("wd5", "wd3", "wd1"):
            try_url = (
                f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
            )
            try:
                r = httpx.post(try_url, json=payload, headers=headers, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    break
            except Exception:
                continue
        else:
            logger.warning(f"Workday: tutti i tentativi falliti per {tenant}/{site}")
            return []

        jobs = []
        for p in data.get("jobPostings", []):
            ext_path = p.get("externalPath", "")
            job_url = f"https://{tenant}.{wd}.myworkdayjobs.com/{site}{ext_path}"
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
