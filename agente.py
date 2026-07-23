import requests
from bs4 import BeautifulSoup
import datetime
import json
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Parole chiave per filtrare bandi per ASD/associazioni sportive
KEYWORDS_ASD = ['asd', 'a.s.d.', 'associazione sportiva', 'associazioni sportive', 'impianto sportivo', 
                'centro sportivo', 'attività sportiva', 'promozione sportiva', 'fondo sport', 'sport giovanile',
                'team sportivo', 'società sportiva', 'sport dilettantistico', 'evento sportivo']

# Parole chiave per escludere bandi chiusi
KEYWORDS_CHIUSO = ['chiuso', 'scaduto', 'concluso', 'terminato', 'archiviato', 'esito', 'aggiudicazione',
                   'graduatoria', 'avviso di aggiudicazione', 'esito di gara']

# Parole da escludere (falsi positivi)
KEYWORDS_ESCLUDI = ['sportello', 'trasporti', 'edilizia', 'universale', 'civile', 'scolastica', 
                    'assistenza specialistica', 'orientation desk', 'contribuente']

# Parole chiave per identificare destinatari ASD nel testo completo
KEYWORDS_DESTINATARI_ASD = [
    'associazione sportiva', 'associazioni sportive', 'a.s.d.', 'asd', 'società sportiva',
    'società sportive', 'ssd', 's.s.d.', 'ente del terzo settore', 'ets', 'cooperativa sociale',
    'organizzazione di volontariato', 'odv', 'promozione sociale', 'aps', 'associazione di promozione sociale',
    'dilettantistico', 'sport dilettantistico', 'impianto sportivo', 'centro sportivo', 'attività sportiva',
    'fondo sport', 'sport giovanile', 'giovani e sport', 'movimento sportivo'
]

def is_aperto(titolo, testo=''):
    testo_completo = (titolo + ' ' + testo).lower()
    for kw in KEYWORDS_CHIUSO:
        if kw in testo_completo:
            return False
    return True

def is_per_asd_titolo(titolo, testo=''):
    testo_completo = (titolo + ' ' + testo).lower()
    for kw in KEYWORDS_ESCLUDI:
        if kw in testo_completo:
            return False
    for kw in KEYWORDS_ASD:
        if kw in testo_completo:
            return True
    return False

def analizza_destinatari(url):
    """Entra nel link del bando e cerca nel testo completo i destinatari."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Estrai tutto il testo visibile
        testo_pagina = soup.get_text(separator=' ', strip=True).lower()
        
        # Cerca sezioni specifiche su destinatari
        destinatari_trovati = []
        for kw in KEYWORDS_DESTINATARI_ASD:
            if kw in testo_pagina:
                destinatari_trovati.append(kw)
        
        # Cerca anche pattern tipo "destinatari", "beneficiari", "soggetti ammessi"
        pattern_destinatari = r'(destinatari|beneficiari|soggetti ammessi|chi può presentare|soggetti attuatori|promotori)[\s\S]{0,500}'
        match = re.search(pattern_destinatari, testo_pagina)
        contesto = ''
        if match:
            contesto = match.group(0)[:300]
        
        # Determina se è per ASD
        per_asd = len(destinatari_trovati) > 0
        if not per_asd and contesto:
            # Se il contesto menziona ASD
            per_asd = any(kw in contesto for kw in ['asd', 'a.s.d.', 'associazione sportiva', 'società sportiva'])
        
        return {
            "per_asd": per_asd,
            "destinatari_trovati": destinatari_trovati,
            "contesto_destinatari": contesto
        }
    except Exception as e:
        return {
            "per_asd": False,
            "errore": str(e),
            "destinatari_trovati": [],
            "contesto_destinatari": ""
        }

def cerca_csvnet():
    url = "https://infobandi.csvnet.it/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            link = item['href'] if item['href'].startswith('http') else url + item['href']
            if len(titolo) > 5 and is_aperto(titolo) and 'segnala-un-bando' not in link:
                # Analizza destinatari
                info = analizza_destinatari(link)
                bandi.append({
                    "titolo": titolo[:150], 
                    "link": link,
                    "per_asd": info["per_asd"],
                    "destinatari": info["destinatari_trovati"][:5],
                    "contesto": info["contesto_destinatari"][:200]
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
            titolo = item.get_text(strip=True)
            if len(titolo) > 10 and is_aperto(titolo) and is_per_asd_titolo(titolo):
                link = item['href'] if item['href'].startswith('http') else "https://www.regione.puglia.it" + item['href']
                info = analizza_destinatari(link)
                bandi.append({
                    "titolo": titolo[:150], 
                    "link": link,
                    "per_asd": info["per_asd"],
                    "destinatari": info["destinatari_trovati"][:5],
                    "contesto": info["contesto_destinatari"][:200]
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
            titolo = item.get_text(strip=True)
            if len(titolo) > 10 and is_aperto(titolo) and is_per_asd_titolo(titolo):
                link = item['href'] if item['href'].startswith('http') else url + item['href']
                info = analizza_destinatari(link)
                bandi.append({
                    "titolo": titolo[:150], 
                    "link": link,
                    "per_asd": info["per_asd"],
                    "destinatari": info["destinatari_trovati"][:5],
                    "contesto": info["contesto_destinatari"][:200]
                })
        return {"fonte": nome, "totale": len(bandi), "bandi": bandi[:10]}
    except Exception as e:
        return {"fonte": nome, "errore": str(e)}

def cerca_sportesalute():
    url = "https://www.sportesalute.eu/bandi-e-avvisi.html"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            link = item['href']
            
            if link in ['#', 'bandi-e-avvisi.html', '/bandi-e-avvisi.html', '']:
                continue
                
            if len(titolo) > 10 and is_aperto(titolo):
                if '/bando-' in link or '/avviso-' in link or 'dettaglio' in link or 'id=' in link:
                    link_completo = link if link.startswith('http') else "https://www.sportesalute.eu" + link
                    info = analizza_destinatari(link_completo)
                    bandi.append({
                        "titolo": titolo[:150], 
                        "link": link_completo,
                        "per_asd": info["per_asd"],
                        "destinatari": info["destinatari_trovati"][:5],
                        "contesto": info["contesto_destinatari"][:200]
                    })
        
        # Rimuovi duplicati
        visti = set()
        bandi_unici = []
        for b in bandi:
            if b['link'] not in visti:
                visti.add(b['link'])
                bandi_unici.append(b)
        
        return {"fonte": "Sport e Salute", "totale": len(bandi_unici), "bandi": bandi_unici[:10]}
    except Exception as e:
        return {"fonte": "Sport e Salute", "errore": str(e)}

if __name__ == "__main__":
    risultati = {
        "data": str(datetime.datetime.now()),
        "filtri": {
            "solo_asd": True,
            "solo_aperti": True,
            "analisi_destinatari": True
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
