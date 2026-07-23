import datetime

def cerca_bandi():
    oggi = datetime.datetime.now()
    print(f"[{oggi}] Agente avviato. Ricerca bandi in corso...")
    # Qui metteremo poi il vero scraping
    print("Nessun bando trovato (modalità test).")

if __name__ == "__main__":
    cerca_bandi()
