import requests
from bs4 import BeautifulSoup
import datetime
import json
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

KEYWORDS_CHIUSO = ['chiuso', 'scaduto', 'concluso', 'terminato', 'archiviato', 'esito', 'aggiudicazione',
                   'graduatoria', 'avviso di aggiudicazione', 'esito di gara']

def is_aperto(titolo):
    testo = titolo.lower()
    for kw in KEYWORDS_CHIUSO:
        if kw in testo:
            return False
    return True

def estrai_info_bando(url):
    """Estrae informazioni dettagliate dal testo del bando."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        testo = soup.get_text(separator='\n', strip=True).lower()
        
        # Cerca dotazione finanziaria
        dotazione = ""
        pattern_dotazione = r'(?:dotazione|budget|importo|finanziamento|contributo|somma)[\s\S]{0,100}?(\d[\d\.,]*\s*(?:euro|€|eur))'
        match = re.search(pattern_dotazione, testo)
        if match:
            dotazione = match.group(0)[:150]
        
        # Cerca documenti necessari
        documenti = []
        pattern_docs = r'(documentazione|documenti|allegat|modul|domanda|richiesta|presentazione)[\s\S]{0,200}'
        match = re.search(pattern_docs, testo)
        if match:
            docs_text = match.group(0)
            for doc in ['domanda', 'modulo', 'allegato', 'documento', 'progetto', 'budget', 'preventivo', 'dichiarazione', 'certificato']:
                if doc in docs_text:
                    documenti.append(doc)
        
        # Riassunto oggetto (primi 500 caratteri utili)
        righe = [r for r in testo.split('\n') if len(r) > 50 and len(r) < 500]
        oggetto = righe[0] if righe else ""
        
        # Destinatari
        destinatari = []
        for kw in ['associazione sportiva', 'a.s.d.', 'asd', 'società sportiva', 'ssd', 'ets', 'ente del terzo settore', 'odv', 'aps']:
            if kw in testo:
                destinatari.append(kw)
        
        return {
            "dotazione": dotazione,
            "documenti": list(set(documenti)),
            "oggetto": oggetto[:300],
            "destinatari": list(set(destinatari))
        }
    except Exception as e:
        return {"dotazione": "", "documenti": [], "oggetto": "", "destinatari": [], "errore": str(e)}

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
                if 'scadenza' in testo.lower():
                    scadenza = testo
                    break
            
            ente = ""
            for sibling in heading.find_all_next(['h4', 'h5', 'p'], limit=3):
                testo = sibling.get_text(strip=True)
                if testo and testo != titolo and len(testo) < 100:
                    ente = testo
                    break
            
            info = estrai_info_bando(link_completo)
            bandi.append({
                "titolo": titolo[:150],
                "ente": ente[:100],
                "scadenza": scadenza[:50],
                "link": link_completo,
                "dotazione": info["dotazione"],
                "documenti": info["documenti"],
                "oggetto": info["oggetto"],
                "destinatari": info["destinatari"]
            })
        
        return {"fonte": "CSVNet (filtro: associazioni sportive)", "totale": len(bandi), "bandi": bandi[:15]}
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
                                                  'territori']):
                if not any(x in link.lower() for x in ['bando', 'avviso', 'contributo']):
                    continue
            
            if len(titolo) < 10 or not is_aperto(titolo):
                continue
            
            link_completo = link if link.startswith('http') else "https://www.sportesalute.eu" + link
            if link_completo in visti:
                continue
            visti.add(link_completo)
            
            if any(x in link.lower() for x in ['bando', 'avviso', 'contributo']):
                info = estrai_info_bando(link_completo)
                bandi.append({
                    "titolo": titolo[:150],
                    "ente": "Sport e Salute",
                    "scadenza": "",
                    "link": link_completo,
                    "dotazione": info["dotazione"],
                    "documenti": info["documenti"],
                    "oggetto": info["oggetto"],
                    "destinatari": info["destinatari"]
                })
        
        return {"fonte": "Sport e Salute", "totale": len(bandi), "bandi": bandi[:10]}
    except Exception as e:
        return {"fonte": "Sport e Salute", "errore": str(e)}

def genera_markdown(risultati):
    md = f"""# 📋 Schede Bandi per ASD — {risultati['data']}

## Filtri applicati
- Destinatario: **Associazioni Sportive**
- Solo bandi aperti

---

"""
    for fonte in risultati['fonti']:
        if 'errore' in fonte:
            md += f"## ⚠️ {fonte['fonte']}\nErrore: {fonte['errore']}\n\n"
            continue
        
        md += f"## 📌 {fonte['fonte']} ({fonte['totale']} bandi trovati)\n\n"
        
        for bando in fonte.get('bandi', []):
            md += f"""### 🎯 {bando['titolo']}

| Campo | Dettaglio |
|-------|-----------|
| **Ente** | {bando.get('ente', 'N/D')} |
| **Scadenza** | {bando.get('scadenza', 'N/D')} |
| **Dotazione** | {bando.get('dotazione', 'Da verificare')} |
| **Destinatari** | {', '.join(bando.get('destinatari', [])) if bando.get('destinatari') else 'Da verificare'} |
| **Documenti** | {', '.join(bando.get('documenti', [])) if bando.get('documenti') else 'Da verificare'} |
| **Link** | [Apri bando]({bando['link']}) |

**Oggetto:** {bando.get('oggetto', 'Da estrarre dal link')}

💡 **Scrivi progetto:** Copia il titolo e l'oggetto di questo bando, poi chiedimi "Scrivi un progetto per il bando [titolo]".

---

"""
    return md

if __name__ == "__main__":
    risultati = {
        "data": str(datetime.datetime.now()),
        "filtri": {
            "destinatario": "associazioni sportive",
            "solo_aperti": True
        },
        "fonti": [
            cerca_csvnet(),
            cerca_sportesalute()
        ]
    }
    
    # Salva JSON
    with open('risultati.json', 'w', encoding='utf-8') as f:
        json.dump(risultati, f, ensure_ascii=False, indent=2)
    
    # Genera e salva Markdown
    markdown = genera_markdown(risultati)
    with open('bandi.md', 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"Ricerca completata. Salvati {len(risultati['fonti'])} fonti.")
