from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from time import time
from typing import Protocol
from urllib.parse import quote

from archlens.core.aur import AurInfo, sanitize_text, sanitize_url, valid_version

MAX_URL_BYTES = 3500
MAX_BODY_BYTES = 4 * 1024 * 1024
NAME_RE = re.compile(r"^[A-Za-z0-9@._+][A-Za-z0-9@._+-]*$")
BASE_URL = "https://aur.archlinux.org/rpc/v5/info?"


class TransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


class HttpTransport(Protocol):
    def get(self, url: str, *, timeout: float, max_bytes: int, headers: dict[str, str]) -> HttpResponse: ...


@dataclass(frozen=True)
class AurFetchResult:
    infos: dict[str, AurInfo]
    not_found: frozenset[str]
    failed: frozenset[str]
    errors: tuple[str, ...]
    rate_limited: bool
    requests_made: int


def _url(names: Sequence[str]) -> str:
    return BASE_URL + "&".join("arg%5B%5D=" + quote(name, safe="") for name in names)


class AurClient:
    def __init__(self, transport: HttpTransport, user_agent: str, clock=time) -> None:
        self.transport = transport
        self.user_agent = user_agent
        self.clock = clock

    def plan_batches(self, names: Sequence[str]) -> list[list[str]]:
        valid = sorted({name for name in names if NAME_RE.fullmatch(name) and len(name) <= 255})
        batches: list[list[str]] = []
        for name in valid:
            candidate = [*batches[-1], name] if batches else [name]
            if len(_url(candidate).encode()) <= MAX_URL_BYTES:
                if batches:
                    batches[-1] = candidate
                else:
                    batches.append(candidate)
            else:
                batches.append([name])
        return [batch for batch in batches if len(_url(batch).encode()) <= MAX_URL_BYTES]

    def fetch_info(self, names: Sequence[str]) -> AurFetchResult:
        infos: dict[str, AurInfo] = {}
        not_found: set[str] = set()
        failed: set[str] = set()
        errors: list[str] = []
        requests = 0
        for batch in self.plan_batches(names):
            try:
                response = self.transport.get(
                    _url(batch), timeout=20, max_bytes=MAX_BODY_BYTES,
                    headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                )
                requests += 1
            except TransportError as exc:
                failed.update(batch)
                errors.append(sanitize_text(str(exc), 200))
                continue
            if response.status == 429:
                failed.update(batch)
                return AurFetchResult(infos, frozenset(not_found), frozenset(failed), tuple(errors + ["rate limited"]), True, requests)
            if response.status != 200:
                failed.update(batch)
                errors.append(f"HTTP {response.status}")
                continue
            try:
                payload = json.loads(response.body)
                results = payload["results"]
                if payload.get("version") != 5 or payload.get("type") not in {"multiinfo", "error"}:
                    raise ValueError("invalid AUR response")
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                failed.update(batch)
                errors.append(sanitize_text(str(exc), 200))
                continue
            found = set()
            for item in results if isinstance(results, list) else ():
                name = item.get("Name") if isinstance(item, dict) else None
                version = item.get("Version") if isinstance(item, dict) else None
                if name not in batch or not valid_version(version):
                    continue
                found.add(name)
                infos[name] = AurInfo(
                    name=name, package_base=sanitize_text(item.get("PackageBase"), 200),
                    version=version, description=sanitize_text(item.get("Description"), 500),
                    url=sanitize_url(item.get("URL")), num_votes=item.get("NumVotes") if isinstance(item.get("NumVotes"), int) else None,
                    popularity=item.get("Popularity") if isinstance(item.get("Popularity"), (int, float)) else None,
                    out_of_date=item.get("OutOfDate") if isinstance(item.get("OutOfDate"), int) else None,
                    maintainer=sanitize_text(item.get("Maintainer"), 200) or None,
                    first_submitted=item.get("FirstSubmitted") if isinstance(item.get("FirstSubmitted"), int) else None,
                    last_modified=item.get("LastModified") if isinstance(item.get("LastModified"), int) else None,
                    depends=tuple(sanitize_text(x, 200) for x in item.get("Depends", []) if isinstance(x, str))[:200],
                    make_depends=tuple(sanitize_text(x, 200) for x in item.get("MakeDepends", []) if isinstance(x, str))[:200],
                    check_depends=tuple(sanitize_text(x, 200) for x in item.get("CheckDepends", []) if isinstance(x, str))[:200],
                    opt_depends=tuple(sanitize_text(x, 200) for x in item.get("OptDepends", []) if isinstance(x, str))[:200],
                    fetched_at=int(self.clock()),
                )
            not_found.update(set(batch) - found)
        return AurFetchResult(infos, frozenset(not_found), frozenset(failed), tuple(errors), False, requests)
