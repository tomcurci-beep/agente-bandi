import requests
from bs4 import BeautifulSoup
import datetime
import json

def cerca_bandi_bandiattivi():
    url = "https://www.bandiattivi.it/bandi/?s=puglia"
    headers = {'User-Agent': 'Mozilla/5.0'}
    risultati = []
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        bandi = soup.find_all('h2', class_='entry-title') or soup.find_all('article')
        
        for bando in bandi[:10]:
            titolo = bando.get_text(strip=True)
            link = bando.find('a')['href'] if bando.find('a') else 'N/A'
            risultati.append({"titolo": titolo[:100], "link": link})
            
    except Exception as e:
        risultati.append({"errore": str(e)})
    
    # Salva su file
    with open('risultati.json', 'w', encoding='utf-8') as f:
        json.dump({
            "data": str(datetime.datetime.now()),
            "fonte": "BandiAttivi",
            "totale": len(risultati),
            "bandi": risultati
        }, f, ensure_ascii=False, indent=2)
    
    print(f"Salvati {len(risultati)} risultati in risultati.json")

if __name__ == "__main__":
    cerca_bandi_bandiattivi()
