from __future__ import annotations
import shelve
from pathlib import Path

import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("DB_PATH", "data/events.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class Engine:

    def __init__(self, db_path: Path | str = DB_PATH):
        self._db_path = Path(db_path)

    def add_participant(self, msg_id: int | str, participant: str) -> None:
        key = str(msg_id)
        with shelve.open(str(self._db_path), writeback=True) as db:
            if key not in db:
                raise KeyError(f"Aucun évènement avec l'id {msg_id!r} dans la base.")

            ev = db[key]
            ev.setdefault("participants", [])
            if participant not in ev["participants"]:
                ev["participants"].append(participant)
                ev["participants"].sort()

            ctf_key = str(ev.get("ctftime_id", ""))
            if ctf_key:
                db[ctf_key] = ev

    def remove_participant(self, msg_id: int | str, participant: str) -> None:
        key = str(msg_id)
        with shelve.open(str(self._db_path), writeback=True) as db:
            if key not in db:
                raise KeyError(f"Aucun évènement avec l'id {msg_id!r} dans la base.")

            ev = db[key]
            participants = set(ev.get("participants", []))
            participants.discard(participant)
            ev["participants"] = sorted(participants)

            # ► réplique vers ctftime_id si présent
            ctf_key = str(ev.get("ctftime_id", ""))
            if ctf_key:
                db[ctf_key] = ev

    def get_event_info_by_msgid(self, msg_id: int | str):
        key = str(msg_id)
        with shelve.open(str(self._db_path)) as db:
            if key not in db:
                raise KeyError(f"Aucun évènement avec l'id {msg_id!r} dans la base.")
            # On renvoie une copie
            return dict(db[key])

    def get_event_info_by_ctftime(self, ctftime_id: int | str):
        key = str(ctftime_id)
        with shelve.open(str(self._db_path)) as db:
            if key in db:
                return dict(db[key])

            for ev in db.values():
                if str(ev.get("ctftime_id")) == key:
                    return dict(ev)

        raise KeyError(f"Aucun évènement avec le ctftime_id {ctftime_id!r} dans la base.")