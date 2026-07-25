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

import requests
import bs4
from datetime import datetime, timedelta
import re

url = "https://www.wbe.be/vie-a-lecole/calendrier-scolaire/"

response = requests.get(url)
response.raise_for_status()
html = response.text

soup = bs4.BeautifulSoup(html, 'html.parser')
text = soup.get_text(separator="\n")

day_pattern = r"(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)?"
pattern = re.compile(
    rf"(.+?)\s*:\s*(?:du\s+)?{day_pattern}\s*(\d{{1,2}})\s+(\w+)\s+(\d{{4}})(?:\s*au\s*{day_pattern}\s*(\d{{1,2}})\s+(\w+)\s+(\d{{4}}))?",
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

# Le site du WBE ne publie les congés que pour les 1-2 prochaines années
# scolaires. On complète automatiquement les années manquantes pour couvrir
# les 3 prochaines années scolaires, afin que le calendrier ne soit jamais
# "vide" en fin de période connue.
#
# Depuis la réforme des rythmes scolaires de 2022 (Pacte pour un Enseignement
# d'Excellence), les grandes vacances ne courent plus de juillet à fin août :
# elles ont été raccourcies à 7 semaines (les 2 semaines retirées ont été
# redistribuées aux congés de Toussaint et de Pâques, désormais sur 2
# semaines). Le ministère a déjà fixé et publié les dates jusqu'en 2031 ;
# on les utilise donc telles quelles plutôt que de deviner.
# Source : https://www.rtbf.be/article/calendrier-scolaire-quelles-seront-les-dates-de-rentree-et-des-vacances-jusqu-en-2032-10761315
VACANCES_ETE_OFFICIELLES = {
    2026: (datetime(2026, 7, 4), datetime(2026, 8, 23)),
    2027: (datetime(2027, 7, 3), datetime(2027, 8, 29)),
    2028: (datetime(2028, 7, 7), datetime(2028, 8, 27)),
    2029: (datetime(2029, 7, 6), datetime(2029, 8, 26)),
    2030: (datetime(2030, 7, 5), datetime(2030, 8, 25)),
    2031: (datetime(2031, 7, 4), datetime(2031, 8, 24)),
}

NB_ANNEES_A_COUVRIR = 3

annees_ete_connues = {
    c[1].year for c in conges if "été" in c[0].lower()
}

annees_cibles = range(today.year, today.year + NB_ANNEES_A_COUVRIR + 1)
for annee in annees_cibles:
    if annee in annees_ete_connues:
        continue
    if annee in VACANCES_ETE_OFFICIELLES:
        debut, fin = VACANCES_ETE_OFFICIELLES[annee]
        nom = f"Vacances d'été {annee}"
    else:
        # Au-delà du calendrier officiel publié : approximation basée sur la
        # durée typique post-réforme (~7 semaines, début juillet à fin août).
        debut = datetime(annee, 7, 1)
        fin = datetime(annee, 8, 24)
        nom = f"Vacances d'été {annee} (estimation)"
    if fin < today:
        continue
    conges.append((nom, debut, fin))

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
