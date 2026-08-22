"""
Logica di filtro: blacklist, whitelist, città, canale di destinazione.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from .normalizer import normalize, normalize_location

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Risultato del filtro: dove va il job (o None se scartato)"""

    channel: Optional[str]  # "strong" | "review" | None
    reason: str
    city_match: Optional[str] = None
    role_match: Optional[str] = None


def _matches_any(text: str, patterns: list) -> Optional[str]:
    """Ritorna il primo pattern che matcha, o None"""
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            return pat
    return None


def _classify_seniority(normalized_title: str) -> str:
    """junior | mid | senior | unknown"""
    if re.search(
        r"\bjunior\b|\bentry.?level\b|\bgraduate\b|\bnew grad\b|\bearly career\b",
        normalized_title,
    ):
        return "junior"
    if re.search(r"\bsenior\b|\bstaff\b|\bprincipal\b|\blead\b", normalized_title):
        return "senior"
    if re.search(r"\bmid\b|\bintermediate\b", normalized_title):
        return "mid"
    return "unknown"


def _classify_location(location_text: str, locations_cfg: dict) -> tuple:
    """
    Ritorna (tipo, nome_match):
      tipo = "primary" | "opportunistic" | "remote_eu" | "excluded" | "unknown"
    """
    norm = normalize_location(location_text)

    # Esclusioni esplicite (Milano, Berlino, ecc.)
    for excluded in locations_cfg.get("excluded_locations", []):
        if re.search(r"\b" + re.escape(normalize_location(excluded)) + r"\b", norm):
            return ("excluded", excluded)

    # Città primarie
    for city in locations_cfg.get("primary_cities", []):
        for alias in city["aliases"]:
            if re.search(r"\b" + re.escape(alias) + r"\b", norm):
                return ("primary", city["name"])

    # Città opportunistiche
    for city in locations_cfg.get("opportunistic_cities", []):
        for alias in city["aliases"]:
            if re.search(r"\b" + re.escape(alias) + r"\b", norm):
                return ("opportunistic", city["name"])

    # Remote EU/EMEA
    for pat in locations_cfg.get("remote_patterns", {}).get("accepted", []):
        if re.search(pat, norm, flags=re.IGNORECASE):
            return ("remote_eu", "Remote EU")

    return ("unknown", None)


TOP_TIER_FOR_DATA_ANALYST = {
    "Google",
    "Microsoft",
    "Meta",
    "Apple",
    "Amazon",
    "NVIDIA",
    "Netflix",
    "Spotify",
    "Databricks",
    "Stripe",
    "Datadog",
    "Snowflake",
    "OpenAI",
    "Anthropic",
    "DeepL",
    "Figma",
    "Notion",
    "Airbnb",
    "Cloudflare",
    "Anysphere",
    "Perplexity",
    "Hugging Face",
}


def evaluate_job(
    job_title: str,
    job_location: str,
    company: dict,
    roles_cfg: dict,
    locations_cfg: dict,
) -> FilterResult:
    """
    Valuta un singolo job e decide se e dove notificarlo.
    """
    norm_title = normalize(job_title)

    # 1. Location filter
    loc_type, loc_name = _classify_location(job_location, locations_cfg)
    if loc_type == "excluded":
        return FilterResult(None, f"Location esclusa: {loc_name}")
    if loc_type == "unknown":
        return FilterResult(None, f"Location non target: {job_location}")

    # 2. Blacklist check
    bl_hit = _matches_any(norm_title, roles_cfg.get("blacklist", []))

    # Eccezione: "manager" in blacklist ma "product manager" gia' in blacklist esplicita
    # → nessuna eccezione, blacklist vince sempre
    if bl_hit:
        # Ma prima verifico l'eccezione Junior + AI/ML core
        seniority = _classify_seniority(norm_title)
        is_junior_ai_ml = seniority == "junior" and bl_hit in (None,)  # placeholder
        # L'eccezione junior si applica solo se il pattern in blacklist è "junior"
        # In quel caso, se il titolo contiene un termine AI/ML core, recuperiamo il job
        if "junior" in bl_hit.lower() or "jr" in bl_hit.lower():
            core_hit = _matches_any(norm_title, roles_cfg.get("ai_ml_core_terms", []))
            if core_hit:
                logger.debug(f"Junior recuperato per AI/ML core: {job_title}")
                # Salta blacklist, procedi con matching normale
            else:
                return FilterResult(None, f"Blacklist (junior non AI/ML): {bl_hit}")
        else:
            return FilterResult(None, f"Blacklist: {bl_hit}")

    # 3. Whitelist strong
    strong_hit = _matches_any(norm_title, roles_cfg.get("strong_matches", []))
    review_hit = _matches_any(norm_title, roles_cfg.get("review_matches", []))

    # Data Analyst → solo se top-tier
    if review_hit and "data analyst" in review_hit.lower():
        if company.get("name") not in TOP_TIER_FOR_DATA_ANALYST:
            return FilterResult(
                None, f"Data Analyst non in top-tier: {company['name']}"
            )

    # Junior SWE → solo se top-tier (priority: high)
    if review_hit and "software engineer" in review_hit.lower():
        seniority = _classify_seniority(norm_title)
        if seniority == "junior" and company.get("priority") != "high":
            return FilterResult(None, f"Junior SWE non top-tier: {company['name']}")

    if strong_hit:
        # STRONG in città primaria/remote → canale strong
        # STRONG in città opportunistica → canale review (perche' non e' città top)
        if loc_type in ("primary", "remote_eu"):
            return FilterResult(
                "strong",
                f"Strong match: {strong_hit}",
                city_match=loc_name,
                role_match=strong_hit,
            )
        else:  # opportunistic
            return FilterResult(
                "review",
                f"Strong role ma città opportunistica: {loc_name}",
                city_match=loc_name,
                role_match=strong_hit,
            )

    if review_hit:
        return FilterResult(
            "review",
            f"Review match: {review_hit}",
            city_match=loc_name,
            role_match=review_hit,
        )

    return FilterResult(None, "Nessun match ruolo")
