import requests
from bs4 import BeautifulSoup
import datetime
import json
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

KEYWORDS_CHIUSO = ['chiuso', 'scaduto', 'concluso', 'terminato', 'archiviato', 'esito', 'aggiudicazione',
                   'graduatoria', 'avviso di aggiudicazione', 'esito di gara']

KEYWORDS_DESTINATARI_ASD = [
    'associazione sportiva', 'associazioni sportive', 'a.s.d.', 'asd', 'società sportiva',
    'società sportive', 'ssd', 's.s.d.', 'ente del terzo settore', 'ets', 'cooperativa sociale',
    'organizzazione di volontariato', 'odv', 'promozione sociale', 'aps', 'associazione di promozione sociale',
    'dilettantistico', 'sport dilettantistico', 'impianto sportivo', 'centro sportivo', 'attività sportiva',
    'fondo sport', 'sport giovanile', 'giovani e sport', 'movimento sportivo'
]

def is_aperto(titolo):
    testo = titolo.lower()
    for kw in KEYWORDS_CHIUSO:
        if kw in testo:
            return False
    return True

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
    url = "https://infobandi.csvnet.it/bandi/?destinatario=associazioni-sportive"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        bandi = []
        
        for heading in soup.find_all(['h2', 'h3']):
            titolo = heading.get_text(strip=True)
            if len(titolo) < 5 or not is_aperto(titolo):
                continue
            
            link = None
            for sibling in heading.find_all_next(['a'], limit=10):
                testo_link = sibling.get_text(strip=True).lower()
                if 'apri' in testo_link or 'bando' in testo_link:
                    link = sibling['href']
                    break
            
            if not link:
                continue
                
            link_completo = link if link.startswith('http') else "https://infobandi.csvnet.it" + link
            
            scadenza = ""
            for sibling in heading.find_all_next(['p', 'span', 'div'], limit=5):
                testo = sibling.get_text(strip=True)
                if 'scadenza' in testo.lower() or '/' in testo:
                    scadenza = testo
                    break
            
            ente = ""
            for sibling in heading.find_all_next(['h4', 'h5', 'p'], limit=3):
                testo = sibling.get_text(strip=True)
                if testo and testo != titolo and len(testo) < 100:
                    ente = testo
                    break
            
            info = analizza_destinatari(link_completo)
            bandi.append({
                "titolo": titolo[:150],
                "ente": ente[:100],
                "scadenza": scadenza[:50],
                "link": link_completo,
                "per_asd": info["per_asd"],
                "destinatari": info["destinatari_trovati"][:5],
                "contesto": info["contesto_destinatari"][:200]
            })
        
        return {"fonte": "CSVNet (filtro: associazioni sportive)", "totale": len(bandi), "bandi": bandi[:25]}
    except Exception as e:
        return {"fonte": "CSVNet", "errore": str(e)}

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
            
            if any(x in link.lower() for x in ['.html', 'societa', 'identita', 'partner', 'news', 'foto', 'video', 
                                                  'protocolli', 'whistleblowing', 'trasparente', 'sostenibilita',
                                                  'territori', 'basilicata', 'emilia', 'friuli', 'valle', 'lombardia',
                                                  'piemonte', 'sicilia', 'toscana', 'veneto', 'puglia', 'lazio']):
                if not any(x in link.lower() for x in ['bando', 'avviso', 'contributo']):
                    continue
            
            if len(titolo) < 10 or not is_aperto(titolo):
                continue
            
            link_completo = link if link.startswith('http') else "https://www.sportesalute.eu" + link
            if link_completo in visti:
                continue
            visti.add(link_completo)
            
            if any(x in link.lower() for x in ['bando', 'avviso', 'contributo', 'finanziamento']):
                info = analizza_destinatari(link_completo)
                bandi.append({
                    "titolo": titolo[:150],
                    "ente": "",
                    "scadenza": "",
                    "link": link_completo,
                    "per_asd": info["per_asd"],
                    "destinatari": info["destinatari_trovati"][:5],
                    "contesto": info["contesto_destinatari"][:200]
                })
        
        return {"fonte": "Sport e Salute", "totale": len(bandi), "bandi": bandi[:15]}
    except Exception as e:
        return {"fonte": "Sport e Salute", "errore": str(e)}

def cerca_regione_puglia():
    url = "https://www.regione.puglia.it/bandi-e-avvisi"
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
            
            if link in visti:
                continue
            visti.add(link)
            
            per_asd = any(kw in titolo.lower() for kw in ['sport', 'asd', 'associazione', 'giovanile', 'impianto'])
            
            bandi.append({
                "titolo": titolo[:150],
                "ente": "Regione Puglia",
                "scadenza": "",
                "link": link,
                "per_asd": per_asd,
                "destinatari": [],
                "contesto": "Filtro basato solo sul titolo (verificare manualmente)"
            })
        
        return {"fonte": "Regione Puglia", "totale": len(bandi), "bandi": bandi[:15]}
    except Exception as e:
        return {"fonte": "Regione Puglia", "errore": str(e)}

def cerca_comune(url, nome):
    return {
        "fonte": nome,
        "nota": f"Verificare manualmente su: {url}",
        "totale": 0,
        "bandi": []
    }

if __name__ == "__main__":
    risultati = {
        "data": str(datetime.datetime.now()),
        "filtri": {
            "destinatario": "associazioni sportive",
            "solo_aperti": True,
            "analisi_destinatari": True
        },
        "fonti": [
            cerca_csvnet(),
            cerca_sportesalute(),
            cerca_regione_puglia(),
            cerca_comune("https://www.comune.trani.bt.it/", "Comune di Trani"),
            cerca_comune("https://www.comune.barletta.bt.it/", "Comune di Barletta"),
            cerca_comune("https://www.comune.andria.bt.it/", "Comune di Andria")
        ]
    }
    
    with open('risultati.json', 'w', encoding='utf-8') as f:
        json.dump(risultati, f, ensure_ascii=False, indent=2)
    
    print(f"Ricerca completata. Salvati risultati da {len(risultati['fonti'])} fonti.")
