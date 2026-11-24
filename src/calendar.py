"""
KSEI Monthly Balancepos Calendar (2020-2023)
Verified exact snapshot date strings (YYYYMMDD) for all 48 months.
Accounts for IDX trading day closures (holidays, weekends, New Year's Eve).
"""

import calendar
from typing import Dict, List, Tuple, Optional

# Verified month-end trading snapshot dates on the KSEI archive (2020-2023).
MONTHLY_DATES_2020_2023: Dict[str, str] = {
    "2020-01": "20200131",
    "2020-02": "20200228",
    "2020-03": "20200331",
    "2020-04": "20200430",
    "2020-05": "20200529",
    "2020-06": "20200630",
    "2020-07": "20200730",
    "2020-08": "20200831",
    "2020-09": "20200930",
    "2020-10": "20201027",
    "2020-11": "20201130",
    "2020-12": "20201230",
    "2021-01": "20210129",
    "2021-02": "20210226",
    "2021-03": "20210331",
    "2021-04": "20210430",
    "2021-05": "20210531",
    "2021-06": "20210630",
    "2021-07": "20210730",
    "2021-08": "20210831",
    "2021-09": "20210930",
    "2021-10": "20211029",
    "2021-11": "20211130",
    "2021-12": "20211230",
    "2022-01": "20220131",
    "2022-02": "20220225",
    "2022-03": "20220331",
    "2022-04": "20220428",
    "2022-05": "20220531",
    "2022-06": "20220630",
    "2022-07": "20220729",
    "2022-08": "20220831",
    "2022-09": "20220930",
    "2022-10": "20221031",
    "2022-11": "20221130",
    "2022-12": "20221230",
    "2023-01": "20230131",
    "2023-02": "20230228",
    "2023-03": "20230331",
    "2023-04": "20230428",
    "2023-05": "20230531",
    "2023-06": "20230627",
    "2023-07": "20230731",
    "2023-08": "20230831",
    "2023-09": "20230929",
    "2023-10": "20231031",
    "2023-11": "20231130",
    "2023-12": "20231229",
}


def get_periods_in_range(
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None
) -> List[Tuple[str, str]]:
    """
    Returns list of (period_ym, date_str) tuples.
    Can filter by start_year/end_year OR start_period/end_period (format YYYY-MM).
    """
    if start_period is None:
        start_period = f"{start_year or 2020}-01"
    if end_period is None:
        end_period = f"{end_year or 2023}-12"

    periods = []
    for ym, dt in MONTHLY_DATES_2020_2023.items():
        if start_period <= ym <= end_period:
            periods.append((ym, dt))
    return sorted(periods, key=lambda x: x[0])


def candidate_dates_for_month(year: int, month: int) -> List[str]:
    """
    Fallback date generator if period is not in MONTHLY_DATES_2020_2023.
    Returns days from end of month descending.
    """
    last_day = calendar.monthrange(year, month)[1]
    candidates = []
    for d in range(last_day, max(last_day - 6, 24), -1):
        candidates.append(f"{year}{month:02d}{d:02d}")
    return candidates
