
from ctftime_api.client import CTFTimeClient

import requests

from bs4 import BeautifulSoup

class CTFtime:
    def __init__(self, ctftime_id: int):
        self.ctftime_id = int(ctftime_id)

        # pour les infos solo et online  ( non présent dansz l'api)
        self.resp = requests.get(f"https://ctftime.org/event/{self.ctftime_id}", timeout=10)


    async def fetch(self):
        client = CTFTimeClient()
        try:
            event = await client.get_event_information(self.ctftime_id)
            return event
        finally:
            if hasattr(client, "aclose"):
                await client.aclose()
            else:
                await client.close()



    # verifier si ces infos sont présente dans les infos de la lib
    def solo(self):
        TARGET_TEXT = "This event is limited to individual participation! No global rating points."
        try:
            self.resp.raise_for_status()          
        except requests.RequestException:
            #TODO a gerer
            return False

        soup = BeautifulSoup(self.resp.text, "html.parser")

        for p in soup.find_all("p"):
            b = p.find("b")
            if b and TARGET_TEXT in b.get_text(strip=True):
                return True
        return False

    def online(self):
        TARGET_TEXT = "On-line"
        try:
            self.resp.raise_for_status()          
        except requests.RequestException:
            #TODO a gerer
            return False

        soup = BeautifulSoup(self.resp.text, "html.parser")

        for p in soup.find_all("p"):
            b = p.find("b")
            if b and TARGET_TEXT in b.get_text(strip=True):
                return True
        return False


    @property
    def get(self):
        return self

