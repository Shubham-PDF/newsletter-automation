#!/usr/bin/env python3
"""
BUILDR.ai persistence layer.

SQLite is rebuilt in memory at the start of every run from JSONL files in
history/. At the end of the run, tables are dumped back to JSONL and committed
by the workflow. This keeps git history text-based (small, diffable) while
giving the pipeline real SQL during execution.

Usage:
    from tools.db import Store

    store = Store()                       # loads history/*.jsonl
    if store.is_duplicate(url): ...
    store.record_candidate(item)
    store.mark_featured(item_id, "launches")
    vel = store.star_velocity(days=7)     # {full_name: delta}
    store.save()                          # writes history/*.jsonl back
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR = os.path.join(BASE_DIR, "history")

# table -> (jsonl filename, primary key columns, retention in days or None)
TABLES = {
    "items":       ("items.jsonl",       ["id"],                 30),
    "featured":    ("featured.jsonl",    ["id", "issue_date"],   365),
    "repo_stars":  ("repo_stars.jsonl",  ["full_name", "day"],   120),
    "runs":        ("runs.jsonl",        ["run_id"],             180),
}

SCHEMA = """
CREATE TABLE items (
    id           TEXT PRIMARY KEY,
    canonical    TEXT NOT NULL,
    url          TEXT NOT NULL,
    title        TEXT,
    source       TEXT,
    published_at TEXT,
    first_seen   TEXT NOT NULL,
    score        REAL DEFAULT 0
);
CREATE INDEX idx_items_canonical ON items(canonical);
CREATE INDEX idx_items_first_seen ON items(first_seen);

CREATE TABLE featured (
    id          TEXT NOT NULL,
    section     TEXT NOT NULL,
    issue_date  TEXT NOT NULL,
    title       TEXT,
    url         TEXT,
    PRIMARY KEY (id, issue_date)
);
CREATE INDEX idx_featured_date ON featured(issue_date);

CREATE TABLE repo_stars (
    full_name TEXT NOT NULL,
    day       TEXT NOT NULL,
    stars     INTEGER NOT NULL,
    PRIMARY KEY (full_name, day)
);

CREATE TABLE runs (
    run_id  TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
"""

DROP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "ref_src", "source", "fbclid", "gclid", "mc_cid", "mc_eid",
}


def canonical_url(url: str) -> str:
    """Normalize a URL so tracking params and host variants don't defeat dedupe."""
    s = urlsplit((url or "").strip())
    host = s.netloc.lower()
    for prefix in ("www.", "m.", "amp."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    path = s.path.rstrip("/")
    for suffix in ("/amp", ".amp"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(s.query) if k.lower() not in DROP_PARAMS)
    )
    return urlunsplit(("https", host, path, query, ""))


def item_id(url: str) -> str:
    """Stable short ID derived from the canonical URL. Safe to expose to an LLM."""
    return hashlib.sha1(canonical_url(url).encode("utf-8")).hexdigest()[:12]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class Store:
    def __init__(self, history_dir: str = HISTORY_DIR):
        self.history_dir = history_dir
        os.makedirs(self.history_dir, exist_ok=True)
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._load()

    # ---------- load / save ----------

    def _load(self) -> None:
        for table, (filename, _pk, _ttl) in TABLES.items():
            path = os.path.join(self.history_dir, filename)
            if not os.path.exists(path):
                continue
            rows = []
            with open(path, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"[db] skipping bad line {filename}:{lineno}: {e}")
            if not rows:
                continue
            cols = [r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")]
            placeholders = ",".join("?" * len(cols))
            self.conn.executemany(
                f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                [tuple(r.get(c) for c in cols) for r in rows],
            )
        self.conn.commit()

    def save(self) -> dict:
        """Prune by TTL, then write every table back to JSONL. Returns row counts."""
        self.prune()
        counts = {}
        for table, (filename, pk, _ttl) in TABLES.items():
            path = os.path.join(self.history_dir, filename)
            order = ", ".join(pk)
            rows = self.conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
            os.replace(tmp, path)  # atomic; never leaves a half-written history file
            counts[table] = len(rows)
        return counts

    def prune(self) -> None:
        now = datetime.now(timezone.utc)
        cut = lambda d: (now - timedelta(days=d)).isoformat()
        cutday = lambda d: (now - timedelta(days=d)).strftime("%Y-%m-%d")

        self.conn.execute("DELETE FROM items WHERE first_seen < ?", (cut(TABLES['items'][2]),))
        self.conn.execute("DELETE FROM featured WHERE issue_date < ?", (cutday(TABLES['featured'][2]),))
        self.conn.execute("DELETE FROM repo_stars WHERE day < ?", (cutday(TABLES['repo_stars'][2]),))
        self.conn.execute("DELETE FROM runs WHERE run_id < ?", (cutday(TABLES['runs'][2]),))
        self.conn.commit()

    # ---------- dedupe ----------

    def is_duplicate(self, url: str) -> bool:
        """True if this URL was collected in a previous run (within items TTL)."""
        row = self.conn.execute(
            "SELECT 1 FROM items WHERE canonical = ?", (canonical_url(url),)
        ).fetchone()
        return row is not None

    def was_featured(self, url: str, days: int = 30) -> bool:
        """True if this URL already went out in an issue within `days`."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        row = self.conn.execute(
            "SELECT 1 FROM featured WHERE id = ? AND issue_date >= ?",
            (item_id(url), cutoff),
        ).fetchone()
        return row is not None

    def record_candidate(self, item: dict) -> str:
        """Insert a collected item. Returns its id. Existing rows keep first_seen."""
        iid = item_id(item["url"])
        self.conn.execute(
            """INSERT INTO items (id, canonical, url, title, source, published_at, first_seen, score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET score = MAX(score, excluded.score)""",
            (
                iid,
                canonical_url(item["url"]),
                item["url"],
                item.get("title"),
                item.get("source"),
                item.get("published_at"),
                _utcnow(),
                float(item.get("score", 0) or 0),
            ),
        )
        return iid

    def mark_featured(self, iid: str, section: str, title: str = None,
                      url: str = None, issue_date: str = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO featured (id, section, issue_date, title, url) VALUES (?, ?, ?, ?, ?)",
            (iid, section, issue_date or _today(), title, url),
        )

    # ---------- repo star velocity ----------

    def record_stars(self, full_name: str, stars: int, day: str = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO repo_stars (full_name, day, stars) VALUES (?, ?, ?)",
            (full_name, day or _today(), int(stars)),
        )

    def star_velocity(self, days: int = 7) -> dict:
        """
        Star growth per repo over the window. Repos with only one snapshot are
        omitted, so a repo needs to be tracked for at least two runs before it
        can be ranked on velocity.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self.conn.execute(
            """SELECT full_name,
                      MAX(stars) - MIN(stars) AS delta,
                      COUNT(*)                AS snapshots
                 FROM repo_stars
                WHERE day >= ?
             GROUP BY full_name
               HAVING snapshots > 1
             ORDER BY delta DESC""",
            (cutoff,),
        ).fetchall()
        return {r["full_name"]: r["delta"] for r in rows}

    def repos_featured_since(self, days: int = 60) -> set:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self.conn.execute(
            "SELECT DISTINCT title FROM featured WHERE section = 'repo_radar' AND issue_date >= ?",
            (cutoff,),
        ).fetchall()
        return {r["title"].lower() for r in rows if r["title"]}

    # ---------- run manifest ----------

    def record_run(self, manifest: dict, run_id: str = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, payload) VALUES (?, ?)",
            (run_id or _today(), json.dumps(manifest, ensure_ascii=False, sort_keys=True)),
        )

    def source_health(self, days: int = 7) -> dict:
        """Items collected per source over the window — a feed at 0 is a broken parser."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self.conn.execute(
            """SELECT source, COUNT(*) AS n FROM items
                WHERE first_seen >= ? GROUP BY source ORDER BY n DESC""",
            (cutoff,),
        ).fetchall()
        return {r["source"]: r["n"] for r in rows}

    def close(self) -> None:
        self.conn.close()


# ---------- one-time migration from the existing history/*.json ----------

def migrate_legacy(store: "Store") -> None:
    """Import history/featured_repos.json and featured_articles.json if present."""
    repos_path = os.path.join(store.history_dir, "featured_repos.json")
    if os.path.exists(repos_path):
        with open(repos_path, "r", encoding="utf-8") as f:
            for entry in json.load(f):
                name = entry.get("full_name")
                date = (entry.get("date") or _utcnow())[:10]
                if name:
                    store.mark_featured(
                        item_id(f"https://github.com/{name}"),
                        "repo_radar",
                        title=name,
                        url=f"https://github.com/{name}",
                        issue_date=date,
                    )
        print(f"[db] migrated featured_repos.json")

    arts_path = os.path.join(store.history_dir, "featured_articles.json")
    if os.path.exists(arts_path):
        with open(arts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data if isinstance(data, list) else data.get("articles", [])
        for entry in entries:
            url = entry if isinstance(entry, str) else entry.get("url")
            if not url:
                continue
            date = (entry.get("date") if isinstance(entry, dict) else None) or _utcnow()
            store.mark_featured(
                item_id(url), (entry.get("section") if isinstance(entry, dict) else None) or "unknown",
                title=(entry.get("title") if isinstance(entry, dict) else None),
                url=url, issue_date=date[:10],
            )
        print(f"[db] migrated featured_articles.json")

    store.save()


if __name__ == "__main__":
    import sys
    store = Store()
    if "--migrate" in sys.argv:
        migrate_legacy(store)
    print("rows:", store.save())
    print("source health (7d):", store.source_health())
    print("top star velocity (7d):", list(store.star_velocity().items())[:5])