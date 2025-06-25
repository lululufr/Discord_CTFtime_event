
import requests
from bs4 import BeautifulSoup

class Rss:
    def __init__(self, nouvel_article):
        self.titre = nouvel_article.title
        self.lien = nouvel_article.link
        self.summary = nouvel_article.summary


        # Ca c'est  dégueulasse mais c'est le seul moyen de parser la date
        # TODO a ameliorer
        self.date_debut = nouvel_article.summary.split("\n")[1].split(";")[0].replace("Date:", "").replace("&mdash", "").strip()
        self.date_fin = nouvel_article.summary.split("\n")[1].split(";")[1].replace("Date:", "").replace("&nbsp", "").strip()




        self.weight = nouvel_article.summary.split("\n")[6].replace("<br />", "").split(":")[1].strip()

        self.debug = str(nouvel_article)

        self.ctftime_id = nouvel_article.id.split("/")[-1]  # ID CTFTIME à partir du lien

    def solo(self):
        url = f"https://ctftime.org/event/{self.ctftime_id}"
        TARGET_TEXT = "This event is limited to individual participation! No global rating points."
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()          
        except requests.RequestException:
            #TODO a gerer
            return False

        soup = BeautifulSoup(resp.text, "html.parser")

        for p in soup.find_all("p"):
            b = p.find("b")
            if b and TARGET_TEXT in b.get_text(strip=True):
                return True
        return False

    @property
    def get(self):
        return self


