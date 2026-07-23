import requests
from bs4 import BeautifulSoup
import datetime
import json
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

KEYWORDS_ASD = ['asd', 'a.s.d.', 'associazione sportiva', 'associazioni sportive', 'impianto sportivo', 
                'centro sportivo', 'attività sportiva', 'promozione sportiva', 'fondo sport', 'sport giovanile',
                'team sportivo', 'società sportiva', 'sport dilettantistico', 'evento sportivo']

KEYWORDS_CHIUSO = ['chiuso', 'scaduto', 'concluso', 'terminato', 'archiviato', 'esito', 'aggiudicazione',
                   'graduatoria', 'avviso di aggiudicazione', 'esito di gara']

KEYWORDS_ESCLUDI = ['sportello', 'trasporti', 'edilizia', 'universale', 'civile', 'scolastica', 
                    'assistenza specialistica', 'orientation desk', 'contribuente']

KEYWORDS_DESTINATARI_ASD = [
    'associazione sportiva', 'associazioni sportive', 'a.s.d.', 'asd', 'società sportiva',
    'società sportive', 'ssd', 's.s.d.', 'ente del terzo settore', 'ets', 'cooperativa sociale',
    'organizzazione di volontariato', 'odv', 'promozione sociale', 'aps', 'associazione di promozione sociale',
    'dilettantistico', 'sport dilettantistico', 'impianto sportivo', 'centro sportivo', 'attività sportiva',
    'fondo sport', 'sport giovanile', 'giovani e sport', 'movimento sportivo'
]

LINK_ESCLUSI = ['cerca-bandi', 'chi-siamo', 'contatti', 'privacy', 'cookie', 'home', 'login', 'registrati',
                'newsletter', 'faq', 'about', 'bandi-attivi']

def is_link_valido(link):
    link_lower = link.lower()
    for escluso in LINK_ESCLUSI:
        if escluso in link_lower:
            return False
    if not any(x in link_lower for x in ['bando', 'avviso', 'contributo', 'finanziamento', 'progetto']):
        return False
    return True

def is_aperto(titolo):
    testo = titolo.lower()
    for kw in KEYWORDS_CHIUSO:
        if kw in testo:
            return False
    return True

def is_per_asd_titolo(titolo):
    testo = titolo.lower()
    for kw in KEYWORDS_ESCLUDI:
        if kw in testo:
            return False
    for kw in KEYWORDS_ASD:
        if kw in testo:
            return True
    return False

def analizza_destinatari(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        testo_pagina = soup.get_text(separator=' ', strip=True).lower()
        
        destinatari_trovati = []
        for kw in KEYWORDS_DESTINATARI_ASD:
            if kw in testo_pagina:
                destinatari_trovati.append(kw)
        
        pattern = r'(destinatari|beneficiari|soggetti ammessi)[\s\S]{0,300}'
        match = re.search(pattern, testo_pagina)
        contesto = match.group(0)[:200] if match else ''
        
        per_asd = len(destinatari_trovati) > 0 or any(kw in contesto for kw in ['asd', 'a.s.d.', 'associazione sportiva'])
        
        return {"per_asd": per_asd, "destinatari_trovati": destinatari_trovati, "contesto_destinatari": contesto}
    except:
        return {"per_asd": False, "destinatari_trovati": [], "contesto_destinatari": ""}

def cerca_csvnet():
    url = "https://infobandi.csvnet.it/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        visti = set()
        
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            link = item['href'] if item['href'].startswith('http') else url + item['href']
            
            if len(titolo) < 5 or not is_aperto(titolo) or not is_link_valido(link) or link in visti:
                continue
            visti.add(link)
            
            info = analizza_destinatari(link)
            bandi.append({
                "titolo": titolo[:150], "link": link,
                "per_asd": info["per_asd"], "destinatari": info["destinatari_trovati"][:5],
                "contesto": info["contesto_destinatari"][:200]
            })
        return {"fonte": "CSVNet", "totale": len(bandi), "bandi": bandi[:15]}
    except Exception as e:
        return {"fonte": "CSVNet", "errore": str(e)}

def cerca_regione_puglia():
    url = "https://www.regione.puglia.it/web/bandi"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        visti = set()
        
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            if len(titolo) < 10 or not is_aperto(titolo):
                continue
            
            link = item['href']
            if link.startswith('/'):
                link = "https://www.regione.puglia.it" + link
            elif not link.startswith('http'):
                continue
            
            if link in visti or not is_per_asd_titolo(titolo):
                continue
            visti.add(link)
            
            # NO analisi destinatari qui (troppo lento su Regione Puglia)
            bandi.append({
                "titolo": titolo[:150], "link": link,
                "per_asd": "da_verificare", "destinatari": [],
                "contesto": "Analisi destinatari non effettuata (sito JS-heavy)"
            })
        return {"fonte": "Regione Puglia", "totale": len(bandi), "bandi": bandi[:10]}
    except Exception as e:
        return {"fonte": "Regione Puglia", "errore": str(e)}

def cerca_comune(url, nome):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        visti = set()
        
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            if len(titolo) < 10 or not is_aperto(titolo):
                continue
            
            link = item['href']
            if link.startswith('/'):
                link = url + link.lstrip('/')
            elif not link.startswith('http'):
                link = url + link
            
            if link in visti or not is_per_asd_titolo(titolo):
                continue
            visti.add(link)
            
            # NO analisi destinatari qui (troppo lento su comuni)
            bandi.append({
                "titolo": titolo[:150], "link": link,
                "per_asd": "da_verificare", "destinatari": [],
                "contesto": "Analisi destinatari non effettuata (verificare manualmente)"
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
        visti = set()
        
        for item in soup.find_all('a', href=True):
            titolo = item.get_text(strip=True)
            link = item['href']
            
            if link in ['#', 'bandi-e-avvisi.html', '/bandi-e-avvisi.html', '']:
                continue
            if len(titolo) < 10 or not is_aperto(titolo):
                continue
            
            link_completo = link if link.startswith('http') else "https://www.sportesalute.eu" + link
            if link_completo in visti:
                continue
            visti.add(link_completo)
            
            if '/bando-' in link or '/avviso-' in link or 'dettaglio' in link or 'id=' in link or '.html' in link:
                info = analizza_destinatari(link_completo)
                bandi.append({
                    "titolo": titolo[:150], "link": link_completo,
                    "per_asd": info["per_asd"], "destinatari": info["destinatari_trovati"][:5],
                    "contesto": info["contesto_destinatari"][:200]
                })
        return {"fonte": "Sport e Salute", "totale": len(bandi), "bandi": bandi[:15]}
    except Exception as e:
        return {"fonte": "Sport e Salute", "errore": str(e)}

if __name__ == "__main__":
    risultati = {
        "data": str(datetime.datetime.now()),
        "filtri": {"solo_asd": True, "solo_aperti": True, "analisi_destinatari": "parziale"},
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
