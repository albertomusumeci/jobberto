"""
Jobberto - Entrypoint principale.
Eseguito ogni 5 minuti da Windows Task Scheduler.
"""

import hashlib
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Path setup
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


from src.daily_log import send_daily_log, should_send_daily
from src.fetchers import get_fetcher
from src.filters import evaluate_job
from src.notifier import TelegramNotifier
from src.state import JobState


def setup_logging(log_path: str, level: str):
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def job_hash(company: str, job_id: str, url: str) -> str:
    """Chiave univoca per deduplicazione"""
    raw = f"{company}::{job_id}::{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def main():
    load_dotenv(ROOT / ".env")

    settings = load_yaml(ROOT / "config" / "settings.yaml")
    companies_cfg = load_yaml(ROOT / "config" / "companies.yaml")
    roles_cfg = load_yaml(ROOT / "config" / "roles.yaml")
    locations_cfg = load_yaml(ROOT / "config" / "locations.yaml")

    setup_logging(settings["logs"]["path"], settings["logs"]["level"])
    logger = logging.getLogger("jobberto")

    logger.info("=" * 60)
    logger.info(f"Jobberto — scan avviato {datetime.now().isoformat()}")

    bot_token = os.environ.get(settings["telegram"]["bot_token_env"])
    chat_strong = os.environ.get(settings["telegram"]["strong_channel_env"])
    chat_review = os.environ.get(settings["telegram"]["review_channel_env"])
    if not all([bot_token, chat_strong, chat_review]):
        logger.error("Variabili Telegram mancanti. Interruzione.")
        sys.exit(1)
    notifier = TelegramNotifier(bot_token, chat_strong, chat_review)

    state = JobState(str(ROOT / settings["database"]["path"]))

    # === PRIMER: se il DB è vuoto (prima esecuzione), marca tutti i job come "visti"
    # senza inviare notifiche. Evita lo spam iniziale.
    first_run_marker = ROOT / "data" / ".first_run_done"
    is_first_run = not first_run_marker.exists()
    if is_first_run:
        logger.info(
            "PRIMA ESECUZIONE: modalità primer attiva (nessuna notifica inviata)"
        )
        notifier.send_daily_log(
            "🚀 <b>Jobberto è online!</b>\n\n"
            "Sto indicizzando le offerte attuali di ~60 aziende. "
            "Non riceverai notifiche per questa prima scansione.\n"
            "Dalla prossima esecuzione (~15 min) inizierai a ricevere solo "
            "le <b>nuove</b> offerte pubblicate."
        )

    strong_count = 0
    review_count = 0
    total_jobs = 0
    companies_ok = 0
    companies_err = 0
    errors = []

    companies = [c for c in companies_cfg["companies"] if c.get("enabled", True)]
    logger.info(f"Aziende attive: {len(companies)}")

    for company in companies:
        cname = company["name"]
        cats = company["ats"]
        cslug = company["slug"]
        try:
            fetcher = get_fetcher(cats)
            jobs = fetcher.fetch(cslug)
            total_jobs += len(jobs)
            companies_ok += 1
            logger.info(f"[{cname}] {len(jobs)} job scaricati")

            # Primer per-azienda: se non ho MAI visto job da questa azienda,
            # marca tutti i primi come visti senza notificare (evita spam quando aggiungo aziende)
            import sqlite3

            with sqlite3.connect(str(ROOT / settings["database"]["path"])) as conn:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM seen_jobs WHERE company = ?", (cname,)
                )
                company_seen_count = cur.fetchone()[0]
            company_needs_primer = company_seen_count == 0

            if company_needs_primer and not is_first_run:
                logger.info(f"[{cname}] primer per-azienda attivo (nuova azienda)")

            for job in jobs:
                jkey = job_hash(cname, job.job_id, job.url)
                if state.is_seen(jkey):
                    continue

                result = evaluate_job(
                    job.title, job.location, company, roles_cfg, locations_cfg
                )

                # Primer globale o per-azienda: marca senza notificare
                if is_first_run or company_needs_primer:
                    state.mark_seen(
                        jkey,
                        cname,
                        job.title,
                        job.location,
                        job.url,
                        result.channel or "skip",
                    )
                    continue

                if result.channel:
                    notifier.send_job(
                        channel=result.channel,
                        company=cname,
                        title=job.title,
                        location=job.location,
                        url=job.url,
                        url_native=job.url_native,
                        reason=result.reason,
                    )
                    if result.channel == "strong":
                        strong_count += 1
                    else:
                        review_count += 1
                    logger.info(
                        f"  → {result.channel.upper()}: {job.title} @ {job.location}"
                    )

                state.mark_seen(
                    jkey,
                    cname,
                    job.title,
                    job.location,
                    job.url,
                    result.channel or "skip",
                )

        except Exception as e:
            companies_err += 1
            err_msg = f"{cname} ({cats}/{cslug}): {type(e).__name__}: {str(e)[:200]}"
            errors.append(err_msg)
            logger.error(err_msg)

    # Marca il primer completato
    if is_first_run:
        first_run_marker.parent.mkdir(parents=True, exist_ok=True)
        first_run_marker.touch()
        logger.info(f"Primer completato: {total_jobs} job marcati come già visti")

    state.update_scan_stats(
        strong_count, review_count, total_jobs, companies_ok, companies_err, errors
    )

    logger.info(
        f"Scan completato: {strong_count} strong, {review_count} review, "
        f"{companies_ok} ok, {companies_err} errori"
    )

    dl = settings.get("daily_log", {})
    if dl.get("enabled", True) and not is_first_run:
        if should_send_daily(dl["hour"], dl["minute"], state):
            try:
                send_daily_log(state, notifier, len(companies))
            except Exception as e:
                logger.error(f"Daily log failed: {e}")

    logger.info("Jobberto — scan terminato\n")


if __name__ == "__main__":
    main()
