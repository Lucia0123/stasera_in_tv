# bot telegram

from telegram import error, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler
import scraper
from datetime import datetime, timedelta, time
# from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP tolto in quanto non ha tutte le funzionalità che mi servono
import re
import locale   # per esprimere il mese e il giorno della settimana di una data in italiano

# API-key che identifica il mio bot telegram
BOT_TOKEN = "write_your_token_here"
# lista in cui salvare i chat_id degli utenti interessati
chat_ids = []

async def start (update : Update, context : ContextTypes.DEFAULT_TYPE):
    chat_ids.append(update.effective_chat.id)
    await context.bot.send_message(chat_id = update.effective_chat.id,
                                text = "Ciao " + update.effective_user.first_name + ", sono un bot che offre informazioni sui programmi televisivi!\n" + 
                                "Digita /canali per ricevere informazioni sui canali consultabili, " +
                                "/scegli_data per impostare la data di interesse.\n" +
                                "Se vuoi sapere quali programmi stanno andando in onda in un certo orario, scrivi l'ora che ti interessa in formato HH:MM (ad esempio 14:30 o 01:44)")

async def scelta_canale(update : Update, context : ContextTypes.DEFAULT_TYPE):
    canali = scraper.canali_consultabili()

    # print(canali)
    # Creo i pulsanti (lista di liste di canali)
    keyboard = []   # tastiera inline che conterrà tutte le righe di pulsanti

    # qui creo ogni riga della tastiera da mostrare all'utente
    i = 0
    while i in range(0, len(canali)):
        j = i + 5   # +5 visto che voglio 5 pulsanti per ogni riga
        # passare url = canale["link"] come parametro a InlineKeyboardButton per mandare l'utente al link quando clicca il pulsante
        riga = [InlineKeyboardButton(text = canale["nome"], callback_data = canale["nome"])
            for canale in canali[i:j]] # da indice i ad indice j escluso
        keyboard.append(riga)

        # aggiornamento contatore
        i += 5  # preparo i per la prossima iterazione/riga di pulsanti da creare

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Invio messaggio insieme alla tastiera per scegliere il canale
    await update.message.reply_text(
        "📺 Scegli un canale:",
        reply_markup = reply_markup
    )

async def scelta_data(update : Update, context : ContextTypes.DEFAULT_TYPE):
    # imposto la data massima (stasera in tv dà i palinsesti per massimo 4 giorni in futuro)
    data_odierna = datetime.now().date()
    # creo calendario (da 10 giorni in passato a 3 in futuro)
    date_future = [data_odierna + timedelta(days = i) for i in range(1, 4)]     # da 1 a 3
    date_passate = [data_odierna - timedelta(days = i) for i in range(1, 12)]   # da 1 a 11
    calendario = date_passate + [data_odierna] + date_future
    calendario_ordinato = sorted(calendario)
    print(calendario_ordinato)

    # data (tipo date) non è un oggetto serializzabile in json, quindi prima di passarlo a send_message lo trasformo in stringa
    date = [(data.strftime("%d/%m/%Y")) if data != data_odierna else "🟢 " + data.strftime("%d/%m/%Y") for data in calendario_ordinato]

    keyboard = []
    # qui creo ogni riga della tastiera da mostrare all'utente
    i = 0
    while i in range(0, len(date)):
        j = i + 3   # +3 visto che voglio 3 pulsanti per ogni riga
        riga = [InlineKeyboardButton(text = data, callback_data = data)
            for data in date[i:j]] # da indice i ad indice j escluso
        keyboard.append(riga)

        # aggiornamento contatore
        i += 3  # preparo i per la prossima iterazione/riga di pulsanti da creare

    reply_markup = InlineKeyboardMarkup(keyboard)
    # Invio messaggio insieme alla tastiera per scegliere il canale
    await update.message.reply_text(
        "Seleziona la data:",
        reply_markup = reply_markup
    )

async def scelta_ora(update : Update, context : ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id = update.effective_chat.id,
                                   text = "Inserisci l'orario nel formato **HH:MM** (es. `14:30`).")


# handler per i pulsanti inline (caso di canali e date)
async def callback_pulsante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query   # mi dice quale pulsante è stato cliccato
    print(query)
    await query.answer(text = "Caricamento in corso..", show_alert = False)
    nome_pulsante = query.data    # nome pulsante cliccato dall'utente (può essere una data, un canale o un orario)

    canali = scraper.canali_consultabili()
    
    # espressione per riconoscere il tipo di pulsante (se data o canale)
    data = re.findall(r"\d{2}/\d{2}/\d{4}", nome_pulsante)

    if data:
        locale.setlocale(locale.LC_TIME, 'italian')

        # Data selezionata - puoi fare qualcosa con questa data
        # data_formattata = result.strftime("%A_%d_%B_%Y").lower()  # converto oggetto date in una stringa in formato 24_05_2025
        await query.edit_message_text(
            f"Hai selezionato la data {nome_pulsante}\n"
            f"Ora seleziona il canale digitando /canali"
        )
        
        # devo trovare un modo di salvare la data
        context.user_data["data_selezionata"] = nome_pulsante   # dizionario per salvare dati sull'utente
        # print(context.user_data)

    else:   # caso in cui il pulsante è un canale
        # CONTROLLARE SE IN context.user_data c'è una data_selezionata:
        # SE Sì, PASSARE IL PALINSESTO RELATIVO A QUELLA DATA
        # SE NO, PROSEGUIRE COME SOTTO/PRIMA

        try:
            data_selezionata = context.user_data.get("data_selezionata")
        except UnboundLocalError:
            # se l'utente non ha selezionato nessuna data
            data_selezionata = None

        if(data_selezionata):   # se l'utente ha selezionato una data
            # formatto la data prima di passarlo a scraper.ottieni_palinsesto
            # trasformo la data da stringa a date per poterne modificare il formato,
            # poi la ritrasformo in stringa per passarla a ottieni_palinsesto
            data_selezionata = datetime.strptime(data_selezionata, "%d/%m/%Y").date()
            data_formattata = data_selezionata.strftime("%A_%d_%B_%Y")     # es. lunedì_26_maggio_2025
            # sostituisco ì con i (lunedi, martedi ecc) perché altrimenti non si visiterebbe il link giusto
            data_formattata = data_formattata.replace("ì", "i")
            print(data_formattata, " di tipo ", type(data_formattata))

            # ottengo link e palinsesto
            link_canale_scelto = scraper.ottieni_link_canale(canali, nome_pulsante, data_formattata)
            palinsesto = scraper.ottieni_palinsesto(canali, nome_pulsante, data_formattata)
        else:
            link_canale_scelto = [canale["link"] for canale in canali if canale["nome"] == query.data].pop()
            palinsesto = scraper.ottieni_palinsesto(canali, nome_pulsante)

        palinsesto = "\n".join(palinsesto)
        try:
            await query.edit_message_text(f"Hai selezionato: {nome_pulsante} Link: {link_canale_scelto}\n {palinsesto}")
        
        except error.BadRequest:    # caso in cui il messaggio (palinsesto) mandato è troppo lungo
            # allora divido palinsesto in due
            taglio = len(palinsesto) // 2 # // indica la divisione che restituisce come risultato un int
            print("Lunghezza: ", taglio)
            prima_parte =  palinsesto[:taglio]  # fino a metà
            seconda_parte = palinsesto[taglio:] # da metà a fine stringa
            await query.edit_message_text(f"Hai selezionato: {nome_pulsante} Link: {link_canale_scelto}\n{prima_parte}")
            await query.edit_message_text(f"\n{palinsesto}")

# handler per gestire l'input testuale ricevuto tramite messaggio (per l'orario)
async def gestisci_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = update.message.text
    print("testo: ", testo)
    match = re.findall(r"([0-1][0-9]:[0-5][0-9])|(2[0-3]:[0-5][0-9])", testo)   # verifico che l'ora sia in un formato valido

    if match:
        context.user_data["orario"] = testo
        await update.message.reply_text(
                        f"Attendi qualche secondo per sapere i programmi in onda alle {testo}.") 
        # ottieni_programmi_correnti
        programmi = scraper.ottieni_programmi_correnti(testo)
        for programma in programmi:
            if programma:
                await update.message.reply_text(text = programma)
    else:
        await update.message.reply_text("Formato non valido! Usa HH:MM (es. 14:30)")

if __name__ == "__main__":
    # sto istanziando un oggetto della classe ApplicationBuilder()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    # creo gli handler
    start_handler = CommandHandler("start", start)
    canali_handler = CommandHandler("canali", scelta_canale)
    risposta_pulsante_handler = CallbackQueryHandler(callback_pulsante)
    risposta_messaggio_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, gestisci_input)
    scegli_data_handler = CommandHandler("scegli_data", scelta_data)
    ore_handler = CommandHandler("scegli_ora", scelta_ora)
    # aggiungo gli handler creati ad application
    application.add_handler(start_handler)
    application.add_handler(canali_handler)
    application.add_handler(ore_handler)
    application.add_handler(risposta_pulsante_handler)
    application.add_handler(risposta_messaggio_handler)
    application.add_handler(scegli_data_handler)
    application.run_polling()
