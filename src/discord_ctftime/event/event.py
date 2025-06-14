from __future__ import annotations
import shelve
from pathlib import Path
from typing import Iterable, Dict, Any, List

import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("DB_PATH", "data/events.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class Event:

    def __init__(
        self,
        ctftime_id: str | int,
        msg_id: str | int,
        title: str,
        url: str,
        start: str,
        end: str,
        description: str,
        db_path: Path | str = DB_PATH,
    ):
        self.msg_id = str(msg_id)
        self._db_path = Path(db_path)

        with shelve.open(str(self._db_path)) as db:
            ev_key = str(msg_id)  # clé Discord
            ev = db.get(ev_key, {"id": ev_key})
            ev.update(
                ctftime_id=str(ctftime_id),
                msg_id=str(msg_id),
                title=title,
                url=url,
                start="à venir",
                end="à venir",
                description=description,
            )
            db[str(msg_id)] = ev
            db[str(ctftime_id)] = ev

    def add_participants(self, new_participants: Iterable[str] | str) -> None:
        if isinstance(new_participants, str):
            new_participants = [new_participants]

        with shelve.open(str(self._db_path)) as db:
            ev = db[self.id]
            current = set(ev.get("participants", []))
            current.update(new_participants)
            ev["participants"] = sorted(current)
            db[self.id] = ev

    def remove_participants(self, participants_to_remove: Iterable[str] | str) -> None:
        if isinstance(participants_to_remove, str):
            participants_to_remove = [participants_to_remove]

        with shelve.open(str(self._db_path)) as db:
            ev = db[self.id]
            current = set(ev.get("participants", []))
            current.difference_update(participants_to_remove)
            ev["participants"] = sorted(current)
            db[self.id] = ev

    @property
    def participants(self) -> List[str]:
        with shelve.open(str(self._db_path)) as db:
            return db[self.id].get("participants", [])

    @property
    def info(self) -> Dict[str, Any]:
        with shelve.open(str(self._db_path)) as db:
            return dict(db[self.id])      # copie de sécurité

