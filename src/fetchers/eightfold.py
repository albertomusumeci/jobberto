"""
Fetcher per Eightfold AI (Netflix, PayPal).
Eightfold ha 2 varianti di API pubblica:
  - apply_v2: /api/apply/v2/jobs  (Netflix)
  - pcsx:     /api/pcsx/search    (PayPal)


Config in companies.yaml:
  - name: Netflix
    ats: eightfold
    slug: netflix.com
    eightfold_host: explore.jobs.netflix.net
    eightfold_endpoint_type: apply_v2
    eightfold_domain: netflix.com


  - name: PayPal
    ats: eightfold
    slug: paypal
    eightfold_host: paypal.eightfold.ai
    eightfold_endpoint_type: pcsx
    eightfold_domain: paypal.com
"""

import logging
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class EightfoldFetcher(BaseFetcher):
    name = "eightfold"

    def fetch(self, company: dict) -> List[Job]:
        host = company.get("eightfold_host", "")
        endpoint_type = company.get("eightfold_endpoint_type", "apply_v2")
        domain = company.get("eightfold_domain", company.get("slug", ""))

        if not host:
            logger.warning(
                f"Eightfold: eightfold_host mancante per {company.get('name')}"
            )
            return []

        if endpoint_type == "apply_v2":
            return self._fetch_apply_v2(company, host, domain)
        elif endpoint_type == "pcsx":
            return self._fetch_pcsx(company, host, domain)
        else:
            logger.warning(
                f"Eightfold {company.get('name')}: endpoint_type sconosciuto: {endpoint_type}"
            )
            return []

    def _fetch_apply_v2(self, company: dict, host: str, domain: str) -> List[Job]:
        """Netflix pattern"""
        base_url = f"https://{host}/api/apply/v2/jobs"
        headers = {"User-Agent": "Jobberto/1.0", "Accept": "application/json"}

        all_positions = []
        num_pages = 20
        start = 0
        page_size = 50

        for _ in range(num_pages):
            params = {
                "domain": domain,
                "start": start,
                "num": page_size,
                "sort_by": "new",
            }
            try:
                r = httpx.get(base_url, params=params, headers=headers, timeout=20)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                logger.warning(f"Eightfold apply_v2 {company.get('name')} error: {e}")
                break

            positions = data.get("positions", [])
            if not positions:
                break
            all_positions.extend(positions)

            total = data.get("count", 0)
            start += page_size
            if start >= total:
                break

        jobs = []
        for p in all_positions:
            job_id = str(p.get("id", ""))
            locs = p.get("locations", []) or []
            loc = ", ".join(locs) if isinstance(locs, list) else str(locs)
            job_url = (
                p.get("canonicalPositionUrl") or f"https://{host}/careers/job/{job_id}"
            )

            jobs.append(
                Job(
                    job_id=job_id,
                    title=p.get("name", ""),
                    location=loc,
                    url=job_url,
                    url_native="",
                )
            )
        return jobs

    def _fetch_pcsx(self, company: dict, host: str, domain: str) -> List[Job]:
        """PayPal pattern - GET endpoint, response wrapped in {status, data}"""
        base_url = f"https://{host}/api/pcsx/search"
        headers = {
            "User-Agent": "Mozilla/5.0 Jobberto/1.0",
            "Accept": "application/json",
        }

        all_positions = []
        page_size = 25
        start = 0
        max_pages = 40  # safety: 1000 job max

        for _ in range(max_pages):
            params = {
                "domain": domain,
                "query": "",
                "location": "",
                "start": start,
                "num": page_size,
                "sort_by": "timestamp",
            }
            try:
                r = httpx.get(base_url, params=params, headers=headers, timeout=20)
                r.raise_for_status()
                envelope = r.json()
            except Exception as e:
                logger.warning(f"Eightfold pcsx {company.get('name')} error: {e}")
                break

            # Response wrappata: {"status": 200, "error": {...}, "data": {"positions": [...]}}
            data = envelope.get("data", {}) or {}
            positions = data.get("positions", []) or []
            if not positions:
                break
            all_positions.extend(positions)

            # Se ritorna meno del page_size, è l'ultima pagina
            if len(positions) < page_size:
                break

            start += page_size

        jobs = []
        for p in all_positions:
            job_id = str(p.get("id", ""))
            # Location: preferiamo standardizedLocations (più pulite)
            locs = p.get("standardizedLocations") or p.get("locations") or []
            loc = ", ".join(locs) if isinstance(locs, list) else str(locs)

            # positionUrl è relativo: "/careers/job/274921849525"
            position_path = p.get("positionUrl", "")
            if position_path.startswith("http"):
                job_url = position_path
            elif position_path:
                job_url = f"https://{host}{position_path}"
            else:
                job_url = f"https://{host}/careers/job/{job_id}"

            jobs.append(
                Job(
                    job_id=job_id,
                    title=p.get("name", ""),
                    location=loc,
                    url=job_url,
                    url_native="",
                )
            )
        return jobs
