
from datetime import datetime

def parse_time(s: str):
    s_clean = (s
               .replace("a.m.", "AM")
               .replace("p.m.", "PM"))

    dt = datetime.strptime(s_clean, "%B %d, %Y, %I %p")

    return dt.isoformat()


