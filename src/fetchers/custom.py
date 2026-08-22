"""
Fetcher per aziende con ATS proprietari.


IMPORTANTE: gli endpoint qui possono cambiare nel tempo.
Se un'azienda smette di funzionare, controlla i log giornalieri.
"""

import logging
import re
from typing import List

import httpx

from .base import BaseFetcher, Job

logger = logging.getLogger(__name__)


class GoogleFetcher(BaseFetcher):
    name = "custom_google"

    def fetch(self, slug: str) -> List[Job]:
        url = "https://www.google.com/about/careers/applications/jobs/results/"
        params = {
            "location": "Europe",
            "employment_type": "FULL_TIME",
            "sort_by": "date",
        }
        headers = {"User-Agent": "Mozilla/5.0 Jobberto/1.0"}
        try:
            r = httpx.get(
                url, params=params, headers=headers, timeout=20, follow_redirects=True
            )
            r.raise_for_status()
        except Exception as e:
            logger.warning(f"Google fetch failed: {e}")
            return []

        html = r.text
        jobs = []
        pattern = re.compile(
            r'"job_title"\s*:\s*"([^"]+)"[^}]*?"locations"\s*:\s*\[([^\]]+)\][^}]*?"id"\s*:\s*"([^"]+)"'
        )
        for m in pattern.finditer(html):
            title = m.group(1)
            loc_blob = m.group(2)
            jid = m.group(3)
            loc_match = re.search(r'"display"\s*:\s*"([^"]+)"', loc_blob)
            loc = loc_match.group(1) if loc_match else ""
            jobs.append(
                Job(
                    job_id=jid,
                    title=title,
                    location=loc,
                    url=f"https://www.google.com/about/careers/applications/jobs/results/{jid}",
                    url_native="",
                )
            )
        if not jobs:
            logger.info("Google: nessun job estratto")
        return jobs


class MicrosoftFetcher(BaseFetcher):
    name = "custom_microsoft"

    def fetch(self, slug: str) -> List[Job]:
        url = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
        params = {
            "lc": "Switzerland,Germany,Spain,Austria,Luxembourg,Netherlands,Ireland,United Kingdom",
            "l": "en_us",
            "pg": 1,
            "pgSz": 50,
            "o": "Recent",
        }
        headers = {"User-Agent": "Jobberto/1.0", "Accept": "application/json"}
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning(f"Microsoft fetch failed: {e}")
            return []

        jobs = []
        for j in data.get("operationResult", {}).get("result", {}).get("jobs", []):
            loc_field = j.get("primaryLocation", "")
            if isinstance(loc_field, list):
                loc = ", ".join(loc_field)
            else:
                loc = str(loc_field or "")
            jobs.append(
                Job(
                    job_id=str(j.get("jobId", "")),
                    title=j.get("title", ""),
                    location=loc,
                    url=f"https://jobs.careers.microsoft.com/global/en/job/{j.get('jobId','')}",
                    url_native="",
                )
            )
        return jobs


class MetaFetcher(BaseFetcher):
    name = "custom_meta"

    def fetch(self, slug: str) -> List[Job]:
        logger.info("Meta: fetcher disabilitato (usa LinkedIn Alert dedicato)")
        return []


class AppleFetcher(BaseFetcher):
    name = "custom_apple"

    def fetch(self, slug: str) -> List[Job]:
        url = "https://jobs.apple.com/api/role/search"
        headers = {
            "User-Agent": "Jobberto/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        payload = {
            "query": "",
            "filters": {
                "locations": [
                    "postLocation-CHE",
                    "postLocation-DEU",
                    "postLocation-ESP",
                    "postLocation-AUT",
                    "postLocation-LUX",
                    "postLocation-NLD",
                    "postLocation-IRL",
                    "postLocation-GBR",
                ]
            },
            "page": 1,
            "sort": "newest",
        }
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning(f"Apple fetch failed: {e}")
            return []

        jobs = []
        for j in data.get("res", {}).get("searchResults", []):
            locs = j.get("locations", [])
            loc = locs[0].get("name", "") if locs else ""
            jobs.append(
                Job(
                    job_id=str(j.get("id", "")),
                    title=j.get("postingTitle", ""),
                    location=loc,
                    url=f"https://jobs.apple.com/en-us/details/{j.get('positionId','')}",
                    url_native="",
                )
            )
        return jobs


class AmazonFetcher(BaseFetcher):
    name = "custom_amazon"

    def fetch(self, slug: str) -> List[Job]:
        url = "https://www.amazon.jobs/en/search.json"
        params = {
            "normalized_country_code[]": [
                "CHE",
                "DEU",
                "ESP",
                "AUT",
                "LUX",
                "NLD",
                "IRL",
                "GBR",
            ],
            "result_limit": 100,
            "sort": "recent",
        }
        headers = {"User-Agent": "Jobberto/1.0"}
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning(f"Amazon fetch failed: {e}")
            return []

        jobs = []
        for j in data.get("jobs", []):
            jobs.append(
                Job(
                    job_id=str(j.get("id_icims", "")),
                    title=j.get("title", ""),
                    location=j.get("normalized_location", "") or j.get("location", ""),
                    url=f"https://www.amazon.jobs{j.get('job_path','')}",
                    url_native="",
                )
            )
        return jobs


class OracleFetcher(BaseFetcher):
    name = "custom_oracle"

    def fetch(self, slug: str) -> List[Job]:
        logger.info("Oracle: fetcher non implementato")
        return []


class IBMFetcher(BaseFetcher):
    name = "custom_ibm"

    def fetch(self, slug: str) -> List[Job]:
        url = "https://careers.ibm.com/api/jobs"
        params = {
            "country": "CH,DE,ES,AT,LU,NL,IE,GB",
            "sortBy": "PublishedDate",
            "pageSize": 50,
        }
        headers = {"User-Agent": "Jobberto/1.0", "Accept": "application/json"}
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning(f"IBM fetch failed: {e}")
            return []

        jobs = []
        for j in data.get("queryResult", {}).get("searchResults", []):
            jobs.append(
                Job(
                    job_id=str(j.get("jobId", "")),
                    title=j.get("title", ""),
                    location=j.get("primaryLocation", ""),
                    url=j.get("applyUrl", "")
                    or f"https://careers.ibm.com/job/{j.get('jobId','')}",
                    url_native="",
                )
            )
        return jobs


class RevolutFetcher(BaseFetcher):
    name = "custom_revolut"

    def fetch(self, slug: str) -> List[Job]:
        url = "https://www.revolut.com/api/careers/jobs"
        headers = {"User-Agent": "Jobberto/1.0", "Accept": "application/json"}
        try:
            r = httpx.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning(f"Revolut fetch failed: {e}")
            return []

        jobs = []
        items = data if isinstance(data, list) else data.get("jobs", [])
        for j in items:
            jobs.append(
                Job(
                    job_id=str(j.get("id", "")),
                    title=j.get("text", "") or j.get("title", ""),
                    location=(j.get("categories") or {}).get("location", "")
                    or j.get("location", ""),
                    url=j.get("hostedUrl", "") or j.get("url", ""),
                    url_native="",
                )
            )
        return jobs


CUSTOM_FETCHERS = {
    "custom_google": GoogleFetcher,
    "custom_microsoft": MicrosoftFetcher,
    "custom_meta": MetaFetcher,
    "custom_apple": AppleFetcher,
    "custom_amazon": AmazonFetcher,
    "custom_oracle": OracleFetcher,
    "custom_ibm": IBMFetcher,
    "custom_revolut": RevolutFetcher,
}


def get_custom_fetcher(ats_name: str):
    if ats_name in CUSTOM_FETCHERS:
        return CUSTOM_FETCHERS[ats_name]()
    raise ValueError(f"Custom fetcher non trovato: {ats_name}")


class CustomFetcher(BaseFetcher):
    """Placeholder generico"""

    pass
