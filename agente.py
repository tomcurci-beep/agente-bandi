import requests
from bs4 import BeautifulSoup
import datetime
import json

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def cerca_csvnet():
    url = "https://infobandi.csvnet.it/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        # Estraiamo i link dei bandi
        bandi = []
        for item in soup.find_all('a', href=True):
            if 'bando' in item['href'].lower() or 'avviso' in item['href'].lower():
                bandi.append({
                    "titolo": item.get_text(strip=True)[:100],
                    "link": item['href'] if item['href'].startswith('http') else url + item['href']
                })
        return {"fonte": "CSVNet", "totale": len(bandi), "bandi": bandi[:10]}
    except Exception as e:
        return {"fonte": "CSVNet", "errore": str(e)}

def cerca_regione_puglia():
    url = "https://www.regione.puglia.it/web/bandi"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        for item in soup.find_all('a', href=True):
            testo = item.get_text(strip=True)
            if len(testo) > 10:
                bandi.append({
                    "titolo": testo[:100],
                    "link": item['href'] if item['href'].startswith('http') else "https://www.regione.puglia.it" + item['href']
                })
        return {"fonte": "Regione Puglia", "totale": len(bandi), "bandi": bandi[:10]}
    except Exception as e:
        return {"fonte": "Regione Puglia", "errore": str(e)}

def cerca_comune(url, nome):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        for item in soup.find_all('a', href=True):
            testo = item.get_text(strip=True)
            if 'bando' in testo.lower() or 'avviso' in testo.lower() or 'gara' in testo.lower():
                link = item['href'] if item['href'].startswith('http') else url + item['href']
                bandi.append({"titolo": testo[:100], "link": link})
        return {"fonte": nome, "totale": len(bandi), "bandi": bandi[:10]}
    except Exception as e:
        return {"fonte": nome, "errore": str(e)}

def cerca_sportesalute():
    url = "https://www.sportesalute.gov.it/bandi"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        for item in soup.find_all('a', href=True):
            testo = item.get_text(strip=True)
            if len(testo) > 10:
                bandi.append({
                    "titolo": testo[:100],
                    "link": item['href'] if item['href'].startswith('http') else "https://www.sportesalute.gov.it" + item['href']
                })
        return {"fonte": "Sport e Salute", "totale": len(bandi), "bandi": bandi[:10]}
    except Exception as e:
        return {"fonte": "Sport e Salute", "errore": str(e)}

if __name__ == "__main__":
    risultati = {
        "data": str(datetime.datetime.now()),
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
