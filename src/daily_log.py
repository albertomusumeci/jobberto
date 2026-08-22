"""
Genera e invia il log giornaliero riassuntivo.
"""

import logging
from datetime import datetime, time

from .notifier import TelegramNotifier
from .state import JobState

logger = logging.getLogger(__name__)


def should_send_daily(target_hour: int, target_minute: int, state: JobState) -> bool:
    """Controlla se e' l'ora di inviare il log giornaliero."""
    now = datetime.now()
    today_iso = now.date().isoformat()

    if state.daily_log_already_sent(today_iso):
        return False

    target = time(hour=target_hour, minute=target_minute)
    return now.time() >= target


def send_daily_log(state: JobState, notifier: TelegramNotifier, companies_count: int):
    """Invia il riepilogo giornaliero e marca come inviato."""
    now = datetime.now()
    today_iso = now.date().isoformat()

    stats = state.get_daily_stats(today_iso)

    lines = [
        f"📊 <b>Jobberto — Riepilogo {now.strftime('%d/%m/%Y')}</b>",
        "",
        f"🎯 Match forti oggi: <b>{stats.get('strong_matches', 0)}</b>",
        f"👀 Da valutare oggi: <b>{stats.get('review_matches', 0)}</b>",
        "",
        f"🔍 Scan eseguiti oggi: {stats.get('scans_count', 0)}",
        f"🏢 Aziende OK: {stats.get('companies_ok', 0)}/{companies_count}",
    ]

    err_count = stats.get("companies_error", 0)
    if err_count > 0:
        lines.append(f"⚠️ Aziende con errori: <b>{err_count}</b>")
        last_err = stats.get("last_errors", "")
        if last_err:
            lines.append(f"<code>{last_err[:400]}</code>")

    lines.append("")
    lines.append("💡 Buona giornata di ricerca!")

    text = "\n".join(lines)
    notifier.send_daily_log(text)
    state.mark_daily_log_sent(today_iso)
    logger.info(f"Daily log inviato per {today_iso}")
