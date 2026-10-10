"""The single HTTP helper every source goes through.

It sets a descriptive User-Agent, a 60-second timeout, per-host rate limits,
and three retries with exponential backoff and jitter on 429 and 5xx
responses. A proxy refusal (403 with x-deny-reason) is raised as
NetworkBlocked so callers can report the exact host to allow.
"""
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config

_LAST_CALL = {}

# Minimum seconds between requests per host. NCBI allows 3 per second without
# a key and 10 with one (we use 9); Crossref's public pool allows 5 per second
# (we use 4); ClinicalTrials.gov asks for about 50 per minute; everything else
# defaults to 1 per second.
def _min_interval(host):
    if host.endswith("ncbi.nlm.nih.gov"):
        return 1 / 9 if os.environ.get("NCBI_API_KEY") else 0.36
    if host == "api.crossref.org":
        return 0.25
    if host == "clinicaltrials.gov":
        return 1.25
    if host == "api.openalex.org":
        return 0.2
    if host == "www.ebi.ac.uk":
        return 0.25
    return 1.0


class HttpError(Exception):
    def __init__(self, url, status, body="", reason=""):
        self.url, self.status, self.body, self.reason = url, status, body, reason
        super().__init__(f"HTTP {status} for {url}: {reason or body[:200]}")


class NetworkBlocked(HttpError):
    """Raised when the session's network policy refuses the host."""


def user_agent():
    email = config.contact_email()
    contact = f"; mailto:{email}" if email else ""
    return f"ICEvidenceWatch/1.0 (literature surveillance{contact})"


def _throttle(host):
    gap = _min_interval(host)
    last = _LAST_CALL.get(host, 0.0)
    wait = last + gap - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL[host] = time.monotonic()


def request(url, params=None, data=None, headers=None, timeout=60, retries=3, method=None):
    """Return the response body as text, or raise HttpError / NetworkBlocked."""
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data, doseq=True).encode() if isinstance(data, dict) else data
    host = urllib.parse.urlparse(url).hostname or ""
    hdrs = {"User-Agent": user_agent(), "Accept-Encoding": "identity"}
    if headers:
        hdrs.update(headers)
    attempt = 0
    while True:
        _throttle(host)
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except urllib.error.HTTPError as e:
            text = ""
            try:
                text = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            deny = e.headers.get("x-deny-reason") if e.headers else None
            if e.code == 403 and deny:
                raise NetworkBlocked(url, 403, text, f"blocked by network policy ({deny}) for host {host}")
            retry_after = None
            if e.headers and e.headers.get("Retry-After"):
                try:
                    retry_after = float(e.headers.get("Retry-After"))
                except ValueError:
                    retry_after = None
            retryable = e.code == 429 or 500 <= e.code < 600
            # A very long Retry-After means a quota is exhausted, not a blip.
            if not retryable or attempt >= retries or (retry_after and retry_after > 120):
                raise HttpError(url, e.code, text)
            sleep = retry_after if retry_after else (2 ** attempt) * 2 + random.uniform(0, 1.5)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt >= retries:
                raise HttpError(url, 0, "", f"connection failed: {e}")
            sleep = (2 ** attempt) * 2 + random.uniform(0, 1.5)
        attempt += 1
        time.sleep(sleep)
