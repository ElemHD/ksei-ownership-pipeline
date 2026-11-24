"""
KSEI Balancepos Downloader with Wayback Machine Fallback.
Handles polite rate-limiting, retries, and local caching.
"""

import os
import time
import zipfile
import urllib.request
import ssl
from pathlib import Path
from typing import Optional, Tuple


class KSEIDownloader:
    def __init__(
        self,
        raw_dir: Path,
        delay_seconds: float = 0.5,
        timeout: int = 25,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ):
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self.user_agent = user_agent
        
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def get_raw_filepath(self, date_str: str) -> Path:
        return self.raw_dir / f"BalanceposEfek{date_str}.zip"

    def is_valid_zip(self, file_path: Path) -> bool:
        """
        Validates that the file exists, is larger than 10KB, and has valid zip structure.
        """
        if not file_path.exists() or file_path.stat().st_size < 10000:
            return False
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                txts = [n for n in z.namelist() if n.lower().endswith(".txt")]
                if not txts:
                    return False
                bad_file = z.testzip()
                return bad_file is None
        except Exception:
            return False

    def download_period(
        self,
        date_str: str,
        force: bool = False
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Downloads the balancepos zip file for the given date_str (YYYYMMDD).
        Tries primary KSEI server first, falls back to Wayback Machine if needed.
        
        Returns:
            (success: bool, local_path: Optional[Path], message: str)
        """
        target_path = self.get_raw_filepath(date_str)

        if not force and self.is_valid_zip(target_path):
            return True, target_path, "Cache (Already downloaded)"

        primary_url = f"https://www.ksei.co.id/storage/Download/BalanceposEfek{date_str}.zip"
        wayback_url = f"https://web.archive.org/web/https://www.ksei.co.id/storage/Download/BalanceposEfek{date_str}.zip"

        sources = [
            ("Primary KSEI", primary_url),
            ("Wayback Machine", wayback_url)
        ]

        last_error = ""

        for source_name, url in sources:
            time.sleep(self.delay_seconds)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self.user_agent}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as resp:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    # KSEI returns an HTTP 200 HTML SPA page on missing files instead of 404.
                    if "text/html" in content_type:
                        last_error = f"{source_name} returned 404 HTML SPA page"
                        continue

                    if resp.status == 200:
                        content = resp.read()
                        if len(content) > 10000:
                            temp_path = target_path.with_suffix(".tmp")
                            temp_path.write_bytes(content)
                            if self.is_valid_zip(temp_path):
                                if target_path.exists():
                                    target_path.unlink()
                                temp_path.rename(target_path)
                                return True, target_path, f"OK ({source_name}, {len(content):,} bytes)"
                            else:
                                temp_path.unlink(missing_ok=True)
                                last_error = f"{source_name} returned corrupted zip"
            except Exception as e:
                last_error = f"{source_name} failed: {e}"

        return False, None, last_error
