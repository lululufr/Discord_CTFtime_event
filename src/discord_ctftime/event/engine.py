from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Iterable, Dict, Any, List, ClassVar

import os
from dotenv import load_dotenv

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil import parser

import re

load_dotenv()

class Engine:

    DB_PATH: ClassVar[Path] = Path(os.getenv("DB_PATH", "data/events.sqlite"))
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    _TABLE_EVENTS = "events"
    _TABLE_PARTICIPANTS = "participants"
    _TABLE_MAYBE = "maybe_participants"


    @staticmethod
    def _connection(db_path: Path | str | None = None) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path or Engine.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def _ensure_schema(cls) -> None:
        with cls._connection() as conn:
            conn.executescript(
                f"""
                CREATE TABLE IF NOT EXISTS {cls._TABLE_EVENTS} (
                    ctftime_id  TEXT PRIMARY KEY,
                    msg_id      TEXT UNIQUE,
                    title       TEXT,
                    url         TEXT,
                    start       TEXT,
                    end         TEXT,
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS {cls._TABLE_PARTICIPANTS} (
                    ctftime_id  TEXT,
                    participant TEXT,
                    PRIMARY KEY (ctftime_id, participant),
                    FOREIGN KEY (ctftime_id) REFERENCES {cls._TABLE_EVENTS}(ctftime_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS {cls._TABLE_MAYBE} (
                    ctftime_id  TEXT,
                    participant TEXT,
                    PRIMARY KEY (ctftime_id, participant),
                    FOREIGN KEY (ctftime_id) REFERENCES {cls._TABLE_EVENTS}(ctftime_id)
                        ON DELETE CASCADE
                );
                """
            )
            conn.commit()



    @classmethod
    def _resolve_ctftime(cls, identifier: str) -> str:
        """Retourne le **ctftime_id** à partir d’un *ctftime_id* ou *msg_id*.
        Lève ``KeyError`` si l’évènement n’existe pas.
        """
        with cls._connection() as conn:

            row = conn.execute(
                f"SELECT ctftime_id FROM {cls._TABLE_EVENTS} WHERE ctftime_id = ?",
                (identifier,),
            ).fetchone()
            if row:
                return row["ctftime_id"]


            row = conn.execute(
                f"SELECT ctftime_id FROM {cls._TABLE_EVENTS} WHERE msg_id = ?",
                (identifier,),
            ).fetchone()
            if row:
                return row["ctftime_id"]
        raise KeyError(
            f"Aucun évènement avec l'identifiant {identifier!r} (ctftime_id ou msg_id) dans la base."
        )

    @classmethod
    def _participants(cls, table: str, ctftime_id: str) -> List[str]:
        with cls._connection() as conn:
            rows = conn.execute(
                f"SELECT participant FROM {table} WHERE ctftime_id = ?",
                (ctftime_id,),
            ).fetchall()
            return sorted(r[0] for r in rows)



    def __init__(self):
        pass

    @classmethod
    def new_event(
        cls,
        ctftime_id: str | int,
        msg_id: str | int,
        title: str,
        url: str,
        start: str = "à venir",
        end: str = "à venir",
        description: str = "",
        db_path: Path | str | None = None,
    ) -> "Engine":

        cls._ensure_schema()
        db_path = Path(db_path) if db_path else cls.DB_PATH

        with cls._connection(db_path) as conn:
            conn.execute(
                f"""
                INSERT INTO {cls._TABLE_EVENTS} (
                    ctftime_id, msg_id, title, url, start, end, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ctftime_id) DO UPDATE SET
                    msg_id      = excluded.msg_id,
                    title       = excluded.title,
                    url         = excluded.url,
                    start       = excluded.start,
                    end         = excluded.end,
                    description = excluded.description
                """,
                (
                    str(ctftime_id),
                    str(msg_id),
                    title,
                    url,
                    start,
                    end,
                    description,
                ),
            )
            conn.commit()

        ev = cls.load(ctftime_id)
        ev._db_path = db_path
        return ev

    @classmethod
    def load(cls, identifier: str | int) -> "Engine":

        ctftime_id = cls._resolve_ctftime(str(identifier))
        ev = cls()
        ev.ctftime_id = ctftime_id
        with cls._connection() as conn:
            row = conn.execute(
                f"SELECT msg_id FROM {cls._TABLE_EVENTS} WHERE ctftime_id = ?",
                (ctftime_id,),
            ).fetchone()
            ev.msg_id = row["msg_id"] if row else None
        return ev


    @property
    def info(self) -> Dict[str, Any]:
        if not hasattr(self, "ctftime_id"):
            raise AttributeError("Instance non liée. Utilisez new_event ou load().")
        with self._connection(self._db_path) as conn:
            ev = conn.execute(
                f"SELECT * FROM {self._TABLE_EVENTS} WHERE ctftime_id = ?",
                (self.ctftime_id,),
            ).fetchone()
            if ev is None:
                raise KeyError(f"Évènement introuvable : {self.ctftime_id}")
            data = dict(ev)
            data["participants"] = self._participants(self._TABLE_PARTICIPANTS, self.ctftime_id)
            data["maybe_participants"] = self._participants(self._TABLE_MAYBE, self.ctftime_id)
            return data


    def _bulk(self, table: str, parts: Iterable[str], insert: bool):
        sql = (
            f"INSERT OR IGNORE INTO {table} (ctftime_id, participant) VALUES (?, ?)"
            if insert
            else f"DELETE FROM {table} WHERE ctftime_id = ? AND participant = ?"
        )
        with self._connection(self._db_path) as conn:
            conn.executemany(sql, [(self.ctftime_id, p) for p in parts])
            conn.commit()

    def add_participants(self, participants: Iterable[str] | str):
        parts = [participants] if isinstance(participants, str) else list(participants)
        self._bulk(self._TABLE_PARTICIPANTS, parts, True)

    def remove_participants(self, participants: Iterable[str] | str):
        parts = [participants] if isinstance(participants, str) else list(participants)
        self._bulk(self._TABLE_PARTICIPANTS, parts, False)

    def add_maybe_participants(self, participants: Iterable[str] | str):
        parts = [participants] if isinstance(participants, str) else list(participants)
        self._bulk(self._TABLE_MAYBE, parts, True)

    def remove_maybe_participants(self, participants: Iterable[str] | str):
        parts = [participants] if isinstance(participants, str) else list(participants)
        self._bulk(self._TABLE_MAYBE, parts, False)


    @classmethod
    def _quick_part(cls, table: str, identifier: str, part: str, add: bool):
        ctftime_id = cls._resolve_ctftime(identifier)
        sql = (
            f"INSERT OR IGNORE INTO {table} (ctftime_id, participant) VALUES (?, ?)"
            if add
            else f"DELETE FROM {table} WHERE ctftime_id = ? AND participant = ?"
        )
        with cls._connection() as conn:
            conn.execute(sql, (ctftime_id, part))
            conn.commit()

    @classmethod
    def add_participant(cls, identifier: int | str, participant: str):
        cls._quick_part(cls._TABLE_PARTICIPANTS, str(identifier), participant, True)

    @classmethod
    def remove_participant(cls, identifier: int | str, participant: str):
        cls._quick_part(cls._TABLE_PARTICIPANTS, str(identifier), participant, False)

    @classmethod
    def add_maybe_participant(cls, identifier: int | str, participant: str):
        cls._quick_part(cls._TABLE_MAYBE, str(identifier), participant, True)

    @classmethod
    def remove_maybe_participant(cls, identifier: int | str, participant: str):
        cls._quick_part(cls._TABLE_MAYBE, str(identifier), participant, False)

    @classmethod
    def existe(cls, identifier: str | int) -> bool:
        """Retourne ``True`` si un évènement correspondant à ``identifier`` existe.

        L’``identifier`` peut être un *ctftime_id* **ou** un *msg_id*.
        Contrairement à :py:meth:`_resolve_ctftime`, cette méthode ne lève pas
        d’exception : elle renvoie simplement ``False`` si rien n’est trouvé.
        """
        #cls._ensure_schema()
        with cls._connection() as conn:
            row = conn.execute(
                f"SELECT 1 FROM {cls._TABLE_EVENTS} WHERE ctftime_id = ? OR msg_id = ? LIMIT 1",
                (str(identifier), str(identifier)),
            ).fetchone()
            return row is not None


    @classmethod
    def get_event_info(cls, identifier: int | str) -> Dict[str, Any]:
        """Infos complètes via *ctftime_id* ou *msg_id*."""
        ctftime_id = cls._resolve_ctftime(str(identifier))
        with cls._connection() as conn:
            ev = conn.execute(
                f"SELECT * FROM {cls._TABLE_EVENTS} WHERE ctftime_id = ?",
                (ctftime_id,),
            ).fetchone()
            info = dict(ev)
            info["participants"] = cls._participants(cls._TABLE_PARTICIPANTS, ctftime_id)
            info["maybe_participants"] = cls._participants(cls._TABLE_MAYBE, ctftime_id)
            return info

    @classmethod
    def next_event(cls, now: datetime | None = None) -> Dict[str, Any]:
        now = now or datetime.now(tz=ZoneInfo("Europe/Paris"))
        cls._ensure_schema()

        best_id = best_dt = None

        with cls._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT e.ctftime_id,
                       e.start,
                       (
                         SELECT COUNT(*) FROM {cls._TABLE_PARTICIPANTS} p
                         WHERE p.ctftime_id = e.ctftime_id
                       ) +
                       (
                         SELECT COUNT(*) FROM {cls._TABLE_MAYBE} m
                         WHERE m.ctftime_id = e.ctftime_id
                       ) AS nb_any
                FROM {cls._TABLE_EVENTS} e
                """
            )

            for row in rows:
                raw = row["start"] or ""
                if not raw or "à venir" in raw.lower():
                    continue
                if row["nb_any"] == 0:
                    continue

                clean = re.sub(
                    r"\b([ap])\.?m\.?",
                    lambda m: {"a": "AM", "p": "PM"}[m.group(1).lower()],
                    raw,
                    flags=re.IGNORECASE,
                )

                try:
                    dt = parser.parse(clean, dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    print("⚠️  Parse KO :", raw)
                    continue

                dt = (dt.replace(tzinfo=ZoneInfo("Europe/Paris"))
                      if dt.tzinfo is None
                      else dt.astimezone(ZoneInfo("Europe/Paris")))

                if dt < now:
                    continue

                print("✔️  Candidate :", row["ctftime_id"], dt)

                if best_dt is None or dt < best_dt:
                    best_dt, best_id = dt, row["ctftime_id"]

        if best_id is None:
            raise LookupError("Aucun évènement futur avec des inscrits trouvé.")

        return cls.get_event_info(best_id)


    @classmethod
    def calendar_next_30_days(
        cls,
        now: datetime | None = None,
        span_days: int = 30,  # facile à changer / tester
    ) -> List[Dict[str, Any]]:
        """
        Renvoie la liste des événements prévus dans les `span_days` prochains
        jours (par défaut 30) et pour lesquels il y a au moins un inscrit
        (participants ou maybe).

        La liste est triée du plus proche au plus lointain.
        """
        tz_paris = ZoneInfo("Europe/Paris")
        now = now or datetime.now(tz=tz_paris)
        horizon = now + timedelta(days=span_days)

        cls._ensure_schema()

        candidates: list[tuple[datetime, int]] = []

        with cls._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT e.ctftime_id,
                       e.start,
                       (
                         SELECT COUNT(*) FROM {cls._TABLE_PARTICIPANTS} p
                         WHERE p.ctftime_id = e.ctftime_id
                       ) +
                       (
                         SELECT COUNT(*) FROM {cls._TABLE_MAYBE} m
                         WHERE m.ctftime_id = e.ctftime_id
                       ) AS nb_any
                FROM {cls._TABLE_EVENTS} e
                """
            )

            for row in rows:
                raw = row["start"] or ""
                if not raw or "à venir" in raw.lower():
                    continue
                if row["nb_any"] == 0:
                    continue  # pas d’inscrits

                # Normalisation « AM/PM » éventuelle
                clean = re.sub(
                    r"\b([ap])\\.?m\\.?\\b",
                    lambda m: {"a": "AM", "p": "PM"}[m.group(1).lower()],
                    raw,
                    flags=re.IGNORECASE,
                )

                try:
                    dt = parser.parse(clean, dayfirst=True, fuzzy=True)
                except (ValueError, OverflowError):
                    print("⚠️  Parse KO :", raw)
                    continue


                dt = (
                    dt.replace(tzinfo=tz_paris)
                    if dt.tzinfo is None
                    else dt.astimezone(tz_paris)
                )

                if not (now <= dt <= horizon):
                    continue

                candidates.append((dt, row["ctftime_id"]))

        if not candidates:
            raise LookupError(
                f"Aucun évènement avec des inscrits trouvé dans les {span_days} prochains jours."
            )

        # Trie par date proche
        candidates.sort(key=lambda t: t[0])

        # Retourne la liste d’objets/dicts fournis par get_event_info
        return [cls.get_event_info(eid) for _, eid in candidates]
