import subprocess
import sys

def install_and_import(package, import_name=None):
    try:
        __import__(import_name or package)
    except ImportError:
        print(f"Le package {package} n'est pas installé. Installation en cours...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"{package} installé avec succès.")
    finally:
        globals()[import_name or package] = __import__(import_name or package)

# Installer et importer les dépendances
install_and_import('requests')
install_and_import('beautifulsoup4', 'bs4')

from datetime import datetime, timedelta
import re

url = "https://www.wbe.be/vie-a-lecole/calendrier-scolaire/"

response = requests.get(url)
response.raise_for_status()
html = response.text

soup = bs4.BeautifulSoup(html, 'html.parser')
text = soup.get_text(separator="\n")

pattern = re.compile(
    r"(.+?)\s*:\s*(?:du\s+)?(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)?\s*([0-9]{1,2})\s+(\w+)\s+([0-9]{4})(?:\s*au\s*(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)?\s*([0-9]{1,2})\s+(\w+)\s+([0-9]{4}))?",
    re.IGNORECASE
)

mois_mapping = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12
}

def parse_date(day, month, year):
    month_num = mois_mapping[month.lower()]
    return datetime(int(year), month_num, int(day))

conges = []
for match in pattern.finditer(text):
    nom = match.group(1).strip()
    jour_debut = match.group(2)
    mois_debut = match.group(3)
    annee_debut = match.group(4)
    date_debut = parse_date(jour_debut, mois_debut, annee_debut)

    if match.group(5):
        jour_fin = match.group(5)
        mois_fin = match.group(6)
        annee_fin = match.group(7)
        date_fin = parse_date(jour_fin, mois_fin, annee_fin)
    else:
        date_fin = None

    conges.append((nom, date_debut, date_fin))

today = datetime.today()
conges_futurs = [c for c in conges if c[1] >= today]

def format_date(d):
    return d.strftime("%Y%m%d")

def create_event(uid, name, start, end=None):
    event = []
    event.append("BEGIN:VEVENT")
    event.append(f"UID:{uid}@conges-scolaires.wbe")
    event.append(f"SUMMARY:{name}")
    event.append(f"DTSTART;VALUE=DATE:{format_date(start)}")
    if end:
        event.append(f"DTEND;VALUE=DATE:{format_date(end + timedelta(days=1))}")
    else:
        event.append(f"DTEND;VALUE=DATE:{format_date(start)}")
    event.append("END:VEVENT")
    return "\n".join(event)

ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Perplexity AI//FR\n"
uid = 0
for nom, debut, fin in conges_futurs:
    ics_content += create_event(uid, nom, debut, fin) + "\n"
    uid += 1
ics_content += "END:VCALENDAR\n"

with open("conges_scolaires_wbe_futurs.ics", "w") as f:
    f.write(ics_content)

print("Fichier ICS généré avec succès : conges_scolaires_wbe_futurs.ics")
