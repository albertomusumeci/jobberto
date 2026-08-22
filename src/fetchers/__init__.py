from .ashby import AshbyFetcher
from .custom import CustomFetcher, get_custom_fetcher
from .greenhouse import GreenhouseFetcher
from .lever import LeverFetcher
from .workday import WorkdayFetcher

FETCHERS = {
    "greenhouse": GreenhouseFetcher,
    "lever": LeverFetcher,
    "ashby": AshbyFetcher,
    "workday": WorkdayFetcher,
}


def get_fetcher(ats: str):
    if ats.startswith("custom_"):
        return get_custom_fetcher(ats)
    if ats in FETCHERS:
        return FETCHERS[ats]()
    raise ValueError(f"ATS non supportato: {ats}")
