"""
KSEI Retail / Balancepos Historical Downloader & Parser (2020-2023).
Standalone local tool with Wayback Machine fallback.
"""

import argparse
import sys
import time
from pathlib import Path
import pandas as pd

from src.calendar import get_periods_in_range, MONTHLY_DATES_2020_2023
from src.downloader import KSEIDownloader
from src.parser import KSEIParser, INVESTOR_TYPES


def print_banner():
    banner = r"""
========================================================================
     KSEI Retail Holding / Balancepos Historical Downloader & Parser
                     Period: 2020 - 2023 (Monthly)
========================================================================
    """
    print(banner)


def main():
    parser = argparse.ArgumentParser(
        description="Download and parse KSEI Balancepos / Retail Holding Composition data (2020-2023)."
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Start year, e.g. 2020 (default: 2020)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="End year, e.g. 2023 (default: 2023)"
    )
    parser.add_argument(
        "--start-period",
        type=str,
        default=None,
        help="Specific start period YYYY-MM (e.g. 2020-01)"
    )
    parser.add_argument(
        "--end-period",
        type=str,
        default=None,
        help="Specific end period YYYY-MM (e.g. 2023-12)"
    )
    parser.add_argument(
        "--all-securities",
        action="store_true",
        help="Include all security types (default: Equity only)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force redownload and reparse even if files already exist locally"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Polite delay between HTTP requests in seconds (default: 0.5s)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data",
        help="Base data directory (default: ./data)"
    )

    args = parser.parse_args()

    print_banner()

    base_dir = Path(args.output_dir)
    raw_dir = base_dir / "raw"
    processed_dir = base_dir / "processed"
    output_dir = base_dir / "output"

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    periods = get_periods_in_range(
        start_year=args.start_year,
        end_year=args.end_year,
        start_period=args.start_period,
        end_period=args.end_period
    )
    if not periods:
        print(f"[!] No periods found for specified range.")
        sys.exit(1)

    print(f"[*] Target range: {periods[0][0]} to {periods[-1][0]}")
    print(f"[*] Total periods to process: {len(periods)} months")
    print(f"[*] Security filter: {'ALL SECURITIES' if args.all_securities else 'EQUITY ONLY'}")
    print(f"[*] Storage folders:")
    print(f"    - Raw archives:       {raw_dir.resolve()}")
    print(f"    - Monthly processed:  {processed_dir.resolve()}")
    print(f"    - Consolidated master:{output_dir.resolve()}\n")

    downloader = KSEIDownloader(raw_dir=raw_dir, delay_seconds=args.delay)
    data_parser = KSEIParser(equity_only=not args.all_securities)

    all_dfs = []
    summary_rows = []

    success_count = 0
    start_time = time.time()

    for idx, (ym, date_str) in enumerate(periods, 1):
        prefix = f"[{idx:02d}/{len(periods):02d}] Period {ym} ({date_str}):"
        monthly_csv_path = processed_dir / f"balancepos_retail_{ym}.csv"

        ok, zip_path, msg = downloader.download_period(date_str, force=args.force)
        if not ok or not zip_path:
            print(f"{prefix} FAILED to download -> {msg}")
            continue

        try:
            if not args.force and monthly_csv_path.exists():
                df_month = pd.read_csv(monthly_csv_path, dtype={"Date": str, "Code": str})
                parse_msg = "Cache (Loaded processed CSV)"
            else:
                df_month = data_parser.parse_zip(zip_path)
                df_month.to_csv(monthly_csv_path, index=False)
                parse_msg = f"Parsed ({len(df_month):,} records)"

            all_dfs.append(df_month)
            success_count += 1
            print(f"{prefix} {msg} | {parse_msg}")

            tot_ksei = df_month["total_shares_ksei"].sum()
            tot_retail = df_month["retail_total_shares"].sum()
            tot_local_ret = df_month["retail_local_shares"].sum()
            tot_foreign_ret = df_month["retail_foreign_shares"].sum()
            tot_mkt_val = df_month["total_market_value_idr"].sum()
            tot_ret_val = df_month["retail_total_value_idr"].sum()
            avg_stock_ret_pct = df_month["retail_prop_ksei_pct"].mean()

            summary_rows.append({
                "period": ym,
                "snapshot_date": df_month["Date"].iloc[0] if len(df_month) > 0 else date_str,
                "equities_count": len(df_month),
                "total_ksei_shares": int(tot_ksei),
                "total_retail_shares": int(tot_retail),
                "local_retail_shares": int(tot_local_ret),
                "foreign_retail_shares": int(tot_foreign_ret),
                "market_retail_prop_pct": round((tot_retail / tot_ksei * 100) if tot_ksei > 0 else 0, 4),
                "total_market_value_idr": int(tot_mkt_val),
                "total_retail_value_idr": int(tot_ret_val),
                "market_retail_value_pct": round((tot_ret_val / tot_mkt_val * 100) if tot_mkt_val > 0 else 0, 4),
                "avg_stock_retail_prop_pct": round(avg_stock_ret_pct, 4)
            })

        except Exception as e:
            print(f"{prefix} Error parsing {zip_path.name}: {e}")

    elapsed = time.time() - start_time
    print(f"\n========================================================================")
    print(f"[*] Processing Completed in {elapsed:.1f}s: {success_count}/{len(periods)} periods successful.")

    if all_dfs:
        start_lbl = periods[0][0].replace("-", "")
        end_lbl = periods[-1][0].replace("-", "")
        print("[*] Generating master consolidated outputs...")
        master_df = pd.concat(all_dfs, ignore_index=True)
        master_csv_path = output_dir / f"ksei_retail_balancepos_{start_lbl}_{end_lbl}.csv"
        master_df.to_csv(master_csv_path, index=False)
        print(f"    [+] Master Dataset: {master_csv_path.resolve()} ({len(master_df):,} total rows)")

        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)
            summary_csv_path = output_dir / f"ksei_retail_monthly_summary_{start_lbl}_{end_lbl}.csv"
            summary_df.to_csv(summary_csv_path, index=False)
            print(f"    [+] Monthly Summary:{summary_csv_path.resolve()} ({len(summary_df)} months)")

            print("\n--- Preview: Monthly Retail Proportion Trend ---")
            preview_cols = ["period", "equities_count", "market_retail_prop_pct", "market_retail_value_pct", "avg_stock_retail_prop_pct"]
            print(summary_df[preview_cols].to_string(index=False))

    print(f"========================================================================\n")


if __name__ == "__main__":
    main()
