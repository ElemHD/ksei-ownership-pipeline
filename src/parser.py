"""
KSEI Balancepos Parser & Retail Ownership Calculator.
Extracts pipe-delimited text files from ZIP archives and calculates retail metrics.
"""

import io
import zipfile
from pathlib import Path
from typing import Optional, List
import pandas as pd
import numpy as np


INVESTOR_TYPES = {
    "IS": "Insurance (Asuransi)",
    "CP": "Corporate (Korporasi)",
    "PF": "Pension Fund (Dana Pensiun)",
    "IB": "Financial Institution / Bank (Lembaga Keuangan / Bank)",
    "ID": "Individual / Retail (Individu / Ritel)",
    "MF": "Mutual Fund (Reksadana)",
    "SC": "Securities Company (Perusahaan Efek)",
    "FD": "Foundation (Yayasan)",
    "OT": "Others (Lainnya)"
}


class KSEIParser:
    def __init__(self, equity_only: bool = True):
        self.equity_only = equity_only

    def parse_zip(self, zip_path: Path) -> pd.DataFrame:
        """
        Parses a BalanceposEfek zip file and returns a structured DataFrame
        with retail ownership metrics.
        """
        zip_path = Path(zip_path)
        if not zip_path.exists():
            raise FileNotFoundError(f"File not found: {zip_path}")

        with zipfile.ZipFile(zip_path, "r") as z:
            namelist = z.namelist()
            txt_files = [n for n in namelist if n.lower().endswith(".txt")]
            if not txt_files:
                raise ValueError(f"No .txt file found inside {zip_path.name}")
            
            target_txt = txt_files[0]
            with z.open(target_txt) as f:
                content = f.read().decode("utf-8", errors="ignore")

        df = pd.read_csv(
            io.StringIO(content),
            sep="|",
            dtype=str,
            keep_default_na=False
        )

        # Raw files use 'Total' twice: the first is Local Total, the second is Foreign Total.
        raw_cols = list(df.columns)
        new_cols = []
        seen_total = False
        for c in raw_cols:
            c_clean = c.strip()
            if c_clean.lower() == "total":
                if not seen_total:
                    new_cols.append("Local Total")
                    seen_total = True
                else:
                    new_cols.append("Foreign Total")
            elif c_clean.lower() == "total.1":
                new_cols.append("Foreign Total")
            else:
                new_cols.append(c_clean)
        df.columns = new_cols

        if self.equity_only and "Type" in df.columns:
            df = df[df["Type"].str.strip().str.upper() == "EQUITY"].copy()

        numeric_cols = [
            "Sec. Num", "Price",
            "Local IS", "Local CP", "Local PF", "Local IB", "Local ID", "Local MF", "Local SC", "Local FD", "Local OT", "Local Total",
            "Foreign IS", "Foreign CP", "Foreign PF", "Foreign IB", "Foreign ID", "Foreign MF", "Foreign SC", "Foreign FD", "Foreign OT", "Foreign Total"
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").str.strip(), errors="coerce").fillna(0)

        # Normalize DD-MON-YYYY strings (e.g. 30-DEC-2020) to ISO YYYY-MM-DD.
        if "Date" in df.columns:
            df["Date_Raw"] = df["Date"]
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

        # 'Local ID' and 'Foreign ID' denote domestic and foreign individual (retail) holdings.
        local_id = df["Local ID"] if "Local ID" in df.columns else 0
        foreign_id = df["Foreign ID"] if "Foreign ID" in df.columns else 0
        local_tot = df["Local Total"] if "Local Total" in df.columns else 0
        foreign_tot = df["Foreign Total"] if "Foreign Total" in df.columns else 0
        sec_num = df["Sec. Num"] if "Sec. Num" in df.columns else 0
        price = df["Price"] if "Price" in df.columns else 0

        total_ksei_shares = local_tot + foreign_tot
        retail_total_shares = local_id + foreign_id

        df["total_shares_ksei"] = total_ksei_shares
        df["retail_local_shares"] = local_id
        df["retail_foreign_shares"] = foreign_id
        df["retail_total_shares"] = retail_total_shares

        df["retail_prop_ksei_pct"] = np.where(
            total_ksei_shares > 0,
            (retail_total_shares / total_ksei_shares) * 100.0,
            0.0
        ).round(4)

        df["retail_prop_listed_pct"] = np.where(
            sec_num > 0,
            (retail_total_shares / sec_num) * 100.0,
            0.0
        ).round(4)

        df["retail_local_share_of_local_pct"] = np.where(
            local_tot > 0,
            (local_id / local_tot) * 100.0,
            0.0
        ).round(4)

        df["retail_local_value_idr"] = (local_id * price).astype("int64", errors="ignore")
        df["retail_foreign_value_idr"] = (foreign_id * price).astype("int64", errors="ignore")
        df["retail_total_value_idr"] = (retail_total_shares * price).astype("int64", errors="ignore")
        df["total_market_value_idr"] = (total_ksei_shares * price).astype("int64", errors="ignore")

        return df
