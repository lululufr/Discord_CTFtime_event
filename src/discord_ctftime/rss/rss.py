
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

    @property
    def get(self):
        return self


