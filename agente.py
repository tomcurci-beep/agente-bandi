import requests
from bs4 import BeautifulSoup
import datetime

def cerca_bandi_bandiattivi():
    url = "https://www.bandiattivi.it/bandi/?s=puglia"  # URL di ricerca base
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Estraiamo i titoli dei bandi (questo selettore potrebbe variare)
        bandi = soup.find_all('article', class_='post') or soup.find_all('h2', class_='entry-title')
        
        print(f"[{datetime.datetime.now()}] Trovati {len(bandi)} elementi su BandiAttivi")
        
        for bando in bandi[:5]:  # Primi 5 risultati
            titolo = bando.get_text(strip=True)
            link = bando.find('a')['href'] if bando.find('a') else 'N/A'
            print(f"- {titolo[:80]}... | {link}")
            
    except Exception as e:
        print(f"Errore durante la ricerca: {e}")

if __name__ == "__main__":
    cerca_bandi_bandiattivi()
