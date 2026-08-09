"""Small SEC client with cache-first behavior and fair-access guardrails."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SECClient:
    def __init__(
        self,
        output_dir: Path,
        source_companyfacts_dir: Path | None = None,
        user_agent_env: str = "SEC_USER_AGENT",
        refresh: bool = False,
        rate_limit_per_second: float = 5.0,
        timeout: int = 30,
        logger=None,
        request_logger=None,
    ):
        self.output_dir = Path(output_dir)
        self.companyfacts_cache = self.output_dir / "cache" / "companyfacts"
        self.submissions_cache = self.output_dir / "cache" / "submissions"
        self.companyfacts_cache.mkdir(parents=True, exist_ok=True)
        self.submissions_cache.mkdir(parents=True, exist_ok=True)
        self.source_companyfacts_dir = Path(source_companyfacts_dir) if source_companyfacts_dir else None
        self.user_agent = os.environ.get(user_agent_env, "").strip()
        self.refresh = refresh
        self.min_interval = 1.0 / rate_limit_per_second
        self.timeout = timeout
        self.last_request_at = 0.0
        self.logger = logger
        self.request_logger = request_logger

    def can_request_sec(self):
        return bool(self.user_agent)

    def _log(self, message):
        if self.logger:
            self.logger.info(message)

    def _request_log(self, message):
        if self.request_logger:
            self.request_logger.info(message)

    @staticmethod
    def padded_cik(cik):
        return str(int(str(cik).strip())).zfill(10) if str(cik).strip().isdigit() else str(cik).zfill(10)

    def companyfacts_path(self, cik):
        return self.companyfacts_cache / f"CIK{self.padded_cik(cik)}.json"

    def submissions_path(self, cik):
        return self.submissions_cache / f"CIK{self.padded_cik(cik)}.json"

    def ensure_companyfacts(self, cik):
        cik10 = self.padded_cik(cik)
        target = self.companyfacts_path(cik10)
        if target.exists() and not self.refresh:
            return target, "cache"
        if self.source_companyfacts_dir:
            source = self.source_companyfacts_dir / f"CIK{cik10}.json"
            if source.exists() and not self.refresh:
                shutil.copy2(source, target)
                self._log(f"Copied existing CompanyFacts cache for CIK{cik10}")
                return target, "copied_existing_cache"
        if not self.can_request_sec():
            self._request_log(f"SKIP CIK{cik10} companyfacts: SEC_USER_AGENT missing")
            return None, "sec_user_agent_missing"
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"
        return self._download_json(url, target, f"CIK{cik10} companyfacts")

    def ensure_submissions(self, cik):
        cik10 = self.padded_cik(cik)
        target = self.submissions_path(cik10)
        if target.exists() and not self.refresh:
            return target, "cache"
        if not self.can_request_sec():
            self._request_log(f"SKIP CIK{cik10} submissions: SEC_USER_AGENT missing")
            return None, "sec_user_agent_missing"
        url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
        return self._download_json(url, target, f"CIK{cik10} submissions")

    def _download_json(self, url, target, label):
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            elapsed = time.monotonic() - self.last_request_at
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_request_at = time.monotonic()
            try:
                req = Request(url, headers=headers)
                self._request_log(f"GET {url} attempt={attempt}")
                with urlopen(req, timeout=self.timeout) as response:
                    payload = response.read()
                    parsed = json.loads(payload.decode("utf-8"))
                    target.write_text(json.dumps(parsed), encoding="utf-8")
                    self._request_log(f"OK {label} status={response.status}")
                    return target, "downloaded"
            except HTTPError as exc:
                self._request_log(f"HTTP_ERROR {label} status={exc.code} attempt={attempt}")
                if exc.code in {403, 404}:
                    return None, f"http_{exc.code}"
                if exc.code == 429 or 500 <= exc.code <= 599:
                    time.sleep(min(30, 2**attempt))
                    continue
                return None, f"http_{exc.code}"
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                self._request_log(f"REQUEST_ERROR {label} error={type(exc).__name__} attempt={attempt}")
                time.sleep(min(30, 2**attempt))
        return None, "request_failed"
