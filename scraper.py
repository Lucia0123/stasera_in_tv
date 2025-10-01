# Creare scraper che raccoglie informazioni sui palinsesti di oggi in tv:
# Lo scraper deve esporre le seguenti funzionalità:
# - fornire l'elenco dei canali consultabili -> realizzato in canali_consultabili()
# - fornire il palinsesto completo per un qualsiasi canale e una qualsiasi data (nei limiti di quelle messe a disposizione) -> ottieni_palinsesto()
# - fornire tutti i palinsesto in onda in un dato orario, dove ogni elemento "palinsesto" contiene le seguenti informazioni:
#       orario di inizio, nome del palinsesto, canale su cui va in onda


import requests
from parsel import Selector
from urllib.parse import urljoin
import re
import time
import random
from multiprocessing import Pool

URL = "https://www.staseraintv.com/"

def ottieni_url_assoluto(url_relativo):
    return urljoin(base = URL, url = url_relativo)

# nel sito, il palinsesto di un giorno va dalle 6 di quella mattina fino alle 5 del giorno dopo,
# quindi dal punto di vista temporale le ore 0, 1, 2, 3, 4, 5 vengono dopo le 6 (essendo ore del giorno dopo)
# per poter fare operazioni di confronto tra orari e capire l'orario che viene temporalmente prima fra i due dati,
# devo aggiungere agli orari dopo la mezzanotte un +24
def rendi_confrontabile(orario: str):
    orario_esaminato = float(orario)
    if re.findall(r"0[0-5].[0-9]{2}", orario):
            orario_esaminato += 24
    return orario_esaminato

# funzione che restituisce una lista di dizionari con i nomi di tutti i canali e i link corrispondenti
def canali_consultabili():
    response = requests.get(url = URL)
    selector = Selector(text = response.text, base_url = URL)
    # mi interessa raccogliere due informazioni: la lista dei nomi dei canali
    # e la lista dei link per ogni specifico canale
    nomi_canali = selector.xpath("//*[@class = 'chbuttonsbox']/a/text()").getall()  # nomi dei canali
    url_relativi_canali = selector.xpath("//*[@class = 'chbuttonsbox']/a/@href")    # url relativi dei canali
    url_canali = [ottieni_url_assoluto(url.get()) for url in url_relativi_canali]   # url assoluti dei canali
    canali_consultabili = []   # lista che conterrà le informazioni sui canali
    i = 0   # contatore nel ciclo while
    while i < len(nomi_canali):
        canale = {
            "nome" : nomi_canali[i],
            "link" : url_canali[i]
        }
        canali_consultabili.append(canale)
        i += 1
    # restituisco lista di dizionari dove ogni dizionario ha le informazioni relative a un canale
    return canali_consultabili

# funzione che prende in input un canale e ne restituisce il link corrispondente
# dal dizionario per non dover rifare la richiesta alla pagina per ogni canale chiesto
def ottieni_link_canale(lista_canali: list[dict], canale: str, data = ""):
    # se viene passata una data, sostituisco "stasera" nel link del canale con la data specificata
    for dizionario in lista_canali:   # se il canale dato esiste, ne restituisco il link corrispondente
        if dizionario.get("nome") == canale:
            link = dizionario.get("link")
            if data:    # se è stata specificata una data, restituisco il link specifico per quella data
                nuovo_link = link.replace("_stasera", "_" + data)
                # print(nuovo_link)
                return nuovo_link
            return link  # altrimenti restituisco il link per stasera
    # se sono qui vuol dire che il canale specificato non esiste
    return None

# funzione che prende in input il canale e restituisce il palinsesto corrispondente
def ottieni_palinsesto(lista_canali: list[dict], canale: str, data = ""):
    # la data è un parametro opzionale: se non viene specificata nell'invocazione della funzione,
    # prende di default la data odierna

    # ottengo il link del canale scelto in input
    link_canale = ottieni_link_canale(lista_canali, canale, data)
    # visito il link e ottengo il palinsesto di quel canale
    if link_canale:
        response = requests.get(link_canale)
        selector = Selector(text = response.content.decode(encoding = "utf-8"), encoding = "utf-8")
        # nota: importantissimo specificare l'encoding per la rappresentazione corretta
        # di caratteri speciali come à, ò, ì eccetera

        palinsesto = selector.xpath("//*[@class = 'listingbox']/h4/text()").getall()

        # se il palinsesto è vuoto lancio un'eccezione
        if not palinsesto:
            raise ValueError("Il palinsesto risulta vuoto")

        # esamino gli elementi di palinsesto, se un elemento è vuoto lo elimino dalla lista
        palinsesto_pulito = [p.strip() for p in palinsesto if p.strip()]    # list comprehension
        # se gli elementi sono tutti in uppercase, li trasformo in lowercase (esteticamente più bello)
        # gli altri elementi li mantengo inalterati
        palinsesto_formattato = [p.lower() if p.isupper() else p for p in palinsesto_pulito]
        return palinsesto_formattato
    else:
        return None

# funzione per ottenere i programmi che stanno andando in onda nell'orario di interesse
# thread safe
def ottieni_programma_corrente_di_canale(canali_consultabili: list[dict], orario_di_interesse: str, canale: str):
    # worst case il tempo di esecuzione sarà complessivamente quasi 15, best case quasi 11 secondi
    rnd = random.uniform(0.8, 1.2) # numero randomico fra 0.8 e 1.2 di attesa prima di fare la GET al server per limitare la frequenza delle richieste
    time.sleep(rnd)
    try:
        # Essendo per l'utente importante una risposta veloce, consultare i 56 canale dovrà essere fatto gestendo un thread per canale
        palinsesto = ottieni_palinsesto(canali_consultabili, canale)
    except ValueError:
        return None

    # usare regex per individuare gli orari di inizio e trasformarli in numeri
    # in modo tale da poter fare operazioni di <= e >= su di essi
    orari_programmi = []    # lista in cui salvare gli orari sotto forma di numeri decimali
    if palinsesto:
        for programma in palinsesto:    # per ogni programma nel palinsesto:
            orario_programma = re.findall(pattern = r"\d\d:\d\d", string = programma).pop() # estraggo la parte relativa all'orario
            orario_programma = orario_programma.replace(":", ".")
            orari_programmi.append(orario_programma)
        # print("Orari: ", orari_programmi)  # lista di stringhe

    # fare operazioni di confronto per capire se orario_esaminato è l'orario del programma attualmente in onda

    # rendo gli orari confrontabili
    orari_confrontabili = [rendi_confrontabile(orario_esaminato) for orario_esaminato in orari_programmi]

    orario_di_interesse = rendi_confrontabile(orario_di_interesse.replace(":", "."))

    # trovo l'orario corrente
    indice_corrente = 0
    for orario in orari_confrontabili:
        if orario <= orario_di_interesse:
            # orario viene temporalmente dopo rispetto a orario_di_interesse, quindi visto che la lista è ordinata
            # l'orario corrente sarà all'indice orario - 1
            indice_corrente = orari_confrontabili.index(orario)   # indice del programma che sta andando in onda attualmente!
    orario_corrente = palinsesto[indice_corrente]
    # print("Per canale ", canale, " l'orario corrente è ", orario_corrente)
    # print(time.time())
    return orario_corrente + " su canale " + canale

def ottieni_programmi_correnti(orario: str):
    # PARTE PER OTTENERE I PROGRAMMI CORRENTI PER OGNI CANALE
    lista_canali = canali_consultabili()
    tempo_iniziale = time.time()
    # preparo gli argomenti da passare ad ogni processo
    argomenti = [(lista_canali, orario, canale.get("nome")) for canale in lista_canali]  # primo, secondo, terzo argomento

    # creo i processi
    with Pool(processes = 8) as pool:   # 8 processi in parallelo
        risultati = pool.starmap(func = ottieni_programma_corrente_di_canale, iterable = argomenti)

    # ritardo = 0.5   # ritardo tra una richiesta e l'altra per evitare di danneggiare il server
    # # attendo che finiscano di eseguire
    # for thread in thread_attivi:
    #     thread.join()

    tempo_finale = time.time()
    tempo_di_esecuzione = tempo_finale - tempo_iniziale
    # :.4f per formattare tempo_di_esecuzione con 4 numeri dopo la virgola
    print(f"Il tempo di esecuzione di ottieni_programmi_correnti è stato {tempo_di_esecuzione:.4f} secondi")
    return risultati
    # orari = scraper.ottieni_programmi_correnti(lista_canali, "00:45", "Rai3")
    # print(orari)