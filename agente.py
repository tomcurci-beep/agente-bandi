import requests
from bs4 import BeautifulSoup
import datetime
import json
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Parole chiave per filtrare bandi per ASD/associazioni sportive
KEYWORDS_ASD = ['asd', 'a.s.d.', 'associazione sportiva', 'associazioni sportive', 'sport', 'impianto sportivo', 
                'centro sportivo', 'attività sportiva', 'promozione sportiva', 'fondo sport']

# Parole chiave per escludere bandi chiusi
KEYWORDS_CHIUSO = ['chiuso', 'scaduto', 'concluso', 'terminato', 'archiviato', 'esito', 'aggiudicazione']

def is_aperto(titolo, testo=''):
    testo_completo = (titolo + ' ' + testo).lower()
    for kw in KEYWORDS_CHIUSO:
        if kw in testo_completo:
            return False
    return True

def is_per_asd(titolo, testo=''):
    testo_completo = (titolo + ' ' + testo).lower()
    for kw in KEYWORDS_ASD:
        if kw in testo_completo:
            return True
    return False

def cerca_csvnet():
    url = "https://infobandi.csvnet.it/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            link = item['href'] if item['href'].startswith('http') else url + item['href']
            if is_aperto(titolo) and is_per_asd(titolo):
                bandi.append({"titolo": titolo[:150], "link": link})
        return {"fonte": "CSVNet", "totale": len(bandi), "bandi": bandi[:15]}
    except Exception as e:
        return {"fonte": "CSVNet", "errore": str(e)}

def cerca_regione_puglia():
    url = "https://www.regione.puglia.it/web/bandi"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            if len(titolo) > 10 and is_aperto(titolo) and is_per_asd(titolo):
                link = item['href'] if item['href'].startswith('http') else "https://www.regione.puglia.it" + item['href']
                bandi.append({"titolo": titolo[:150], "link": link})
        return {"fonte": "Regione Puglia", "totale": len(bandi), "bandi": bandi[:15]}
    except Exception as e:
        return {"fonte": "Regione Puglia", "errore": str(e)}

def cerca_comune(url, nome):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            if is_aperto(titolo) and is_per_asd(titolo):
                link = item['href'] if item['href'].startswith('http') else url + item['href']
                bandi.append({"titolo": titolo[:150], "link": link})
        return {"fonte": nome, "totale": len(bandi), "bandi": bandi[:15]}
    except Exception as e:
        return {"fonte": nome, "errore": str(e)}

def cerca_sportesalute():
    url = "https://www.sportesalute.eu/bandi-e-avvisi.html"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        
        # Cerchiamo le sezioni "Bandi aperti" e "Bandi di prossima apertura"
        # Escludiamo "Bandi chiusi" e "Bandi scaduti"
        sezioni_aperte = []
        for heading in soup.find_all(['h2', 'h3', 'h4', 'div']):
            testo = heading.get_text(strip=True).lower()
            if 'apert' in testo or 'prossima apertura' in testo or 'in corso' in testo:
                sezioni_aperte.append(heading)
        
        # Se non troviamo sezioni specifiche, prendiamo tutto e filtriamo
        if not sezioni_aperte:
            items = soup.find_all('a', href=True)
        else:
            items = []
            for sez in sezioni_aperte:
                # Prendiamo i link nella stessa sezione o subito dopo
                for sibling in sez.find_all_next(['a', 'div', 'li'], limit=20):
                    if sibling.name == 'a' and sibling.get('href'):
                        items.append(sibling)
        
        for item in items:
            titolo = item.get_text(strip=True)
            link = item['href'] if item['href'].startswith('http') else "https://www.sportesalute.eu" + item['href']
            if len(titolo) > 5 and is_aperto(titolo) and is_per_asd(titolo):
                bandi.append({"titolo": titolo[:150], "link": link})
        
        return {"fonte": "Sport e Salute", "totale": len(bandi), "bandi": bandi[:15]}
    except Exception as e:
        return {"fonte": "Sport e Salute", "errore": str(e)}

if __name__ == "__main__":
    risultati = {
        "data": str(datetime.datetime.now()),
        "filtri": {
            "solo_asd": True,
            "solo_aperti": True,
            "keywords_asd": KEYWORDS_ASD,
            "keywords_escluse": KEYWORDS_CHIUSO
        },
        "fonti": [
            cerca_csvnet(),
            cerca_regione_puglia(),
            cerca_comune("https://www.comune.trani.bt.it/", "Comune di Trani"),
            cerca_comune("https://www.comune.barletta.bt.it/", "Comune di Barletta"),
            cerca_comune("https://www.comune.andria.bt.it/", "Comune di Andria"),
            cerca_sportesalute()
        ]
    }
    
    with open('risultati.json', 'w', encoding='utf-8') as f:
        json.dump(risultati, f, ensure_ascii=False, indent=2)
    
    print(f"Ricerca completata. Salvati risultati da {len(risultati['fonti'])} fonti.")
