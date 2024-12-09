import json
import requests
import base64
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes
from telegram.ext import filters
from pathlib import Path


# Stati per la conversazione
ASK_MOVIE, ASK_TITLE, ASK_COVER, ASK_YEAR = range(4)

def convert_paths_to_strings(obj):
    if isinstance(obj, Path):
        return str(obj)  # Converte un WindowsPath in una stringa
    elif isinstance(obj, dict):
        return {key: convert_paths_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_paths_to_strings(item) for item in obj]
    else:
        return obj

# File su GitHub (devi aggiornare il tuo URL del repository e il nome del file)
GITHUB_REPO = "https://api.github.com/repos/MrNico98/UploadFilm/contents/movies.json"
GITHUB_TOKEN = "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"

# Funzione per caricare e salvare il file JSON su GitHub
def save_movie_to_github(movies_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(GITHUB_REPO, headers=headers)
    
    if response.status_code == 200:
        file_data = response.json()
        sha = file_data['sha']
        
        # Decodifica solo se ci sono dati nel file
        if file_data.get('content'):
            current_content = base64.b64decode(file_data['content']).decode('utf-8')
            try:
                movies_data_existing = json.loads(current_content)  # Prova a caricare il JSON esistente
            except json.JSONDecodeError:
                print("Errore nel decodificare il JSON esistente, si sta creando un nuovo file.")
                movies_data_existing = {}
        else:
            print("Il file movies.json è vuoto, si sta creando un nuovo file.")
            movies_data_existing = {}

        # Aggiorna i dati del file con quelli nuovi
        movies_data_existing.update(movies_data)
        
        # Converti i percorsi (WindowsPath) in stringhe prima di serializzare in JSON
        movies_data_existing = convert_paths_to_strings(movies_data_existing)
        
        # Crea il JSON aggiornato
        new_data = json.dumps(movies_data_existing, indent=4)
        
        # Codifica il JSON in base64
        encoded_content = base64.b64encode(new_data.encode('utf-8')).decode('utf-8')

        # Richiesta per aggiornare il file su GitHub
        update_payload = {
            "message": "Aggiungi nuovo film",
            "content": encoded_content,
            "sha": sha
        }

        update_response = requests.put(GITHUB_REPO, headers=headers, json=update_payload)

        if update_response.status_code == 200:
            print("Film caricato con successo su GitHub!")
        else:
            print(f"Errore nel caricare il film su GitHub: {update_response.status_code}")
            print(update_response.json())
    else:
        print("Errore nel recuperare il file da GitHub.")



# Funzione per aggiungere un film nel JSON
def add_movie_to_json(title, year, cover_image, movie_file):
    movie_data = {
        title: {
            "title": title,
            "year": year,
            "cover_image": cover_image,
            "movie_file": movie_file
        }
    }
    
    # Salva il film su GitHub
    save_movie_to_github(movie_data)

# Funzione per cercare il film su GitHub
def search_movie_on_github(movie_title):
    # Ottieni il contenuto del file movies.json da GitHub
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(GITHUB_REPO, headers=headers)

    if response.status_code == 200:
        file_data = response.json()
        sha = file_data['sha']
        content = base64.b64decode(file_data['content']).decode('utf-8')
        movies_data = json.loads(content)

        # Cerca il film nel JSON
        movie = movies_data.get(movie_title)

        if movie:
            return movie  # Restituisce i dati del film
        else:
            return None
    else:
        print(f"Errore nel recuperare il file da GitHub: {response.status_code}")
        return None

# Funzione per annullare la conversazione
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operazione annullata. Se vuoi ricominciare, usa /upload.")
    return ConversationHandler.END

# Inizializzazione del comando /upload
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ciao! Mandami il film da caricare.")
    return ASK_MOVIE

# Gestione del film
async def handle_movie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.document:
        # Se il file è un documento
        file_id = update.message.document.file_id
        file_info = await context.bot.get_file(file_id)
        file_path = await file_info.download_to_drive()
        
        # Simulazione conversione in video (qui aggiungi la logica di conversione reale)
        video_file_path = file_path  # In un'implementazione reale, questo diventa il file convertito.
        context.user_data['movie_file'] = video_file_path

        await update.message.reply_text("Hai inviato un file. Verrà inviato come video dopo la conversione.")
    elif update.message.video:
        # Se il file è un video
        context.user_data['movie_file'] = update.message.video.file_id
        await update.message.reply_text("Hai inviato un video.")
    else:
        # Caso in cui non è né documento né video
        await update.message.reply_text("Per favore inviami un file o un video.")
        return ASK_MOVIE

    await update.message.reply_text("Perfetto! Ora dimmi il titolo del film.")
    return ASK_TITLE

# Gestione del titolo del film
async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['movie_title'] = update.message.text
    await update.message.reply_text("Ottimo! Ora mandami l'immagine di copertina.")
    return ASK_COVER

# Gestione dell'immagine di copertina
async def handle_cover(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo:  # Verifica che il messaggio contenga una foto
        await update.message.reply_text("Per favore inviami un'immagine valida.")
        return ASK_COVER

    context.user_data['cover_image'] = update.message.photo[-1].file_id
    await update.message.reply_text("Grazie! Ora dimmi l'anno del film.")
    return ASK_YEAR

# Gestione dell'anno del film
async def handle_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['movie_year'] = update.message.text
    chat_id = "-1002337180747"  # Sostituisci con l'ID del tuo canale

    # Pubblica sul canale: prima il film, poi il titolo e l'anno in messaggi separati
    await context.bot.send_document(
        chat_id=chat_id,
        document=context.user_data['movie_file'],
        caption="Film caricato!"
    )

    # Invia il titolo del film
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Titolo del film: {context.user_data['movie_title']}"
    )

    # Invia l'anno del film
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Anno del film: {context.user_data['movie_year']}"
    )

    # Invia la copertina
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=context.user_data['cover_image'],
    )

    # Salva il film nel JSON
    add_movie_to_json(context.user_data['movie_title'], context.user_data['movie_year'], context.user_data['cover_image'], context.user_data['movie_file'])

    await update.message.reply_text("Film caricato con successo sul canale!")
    return ConversationHandler.END

# Gestione del comando /cerca
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        movie_title = ' '.join(context.args)
        movie = search_movie_on_github(movie_title)

        if movie:
            # Invia il risultato
            await update.message.reply_text(f"Trovato il film")
            await update.message.reply_text(f"Anno: {movie['year']}")
            await update.message.reply_text(f"Titolo: {movie['title']}")

            # Invia la copertina
            await update.message.reply_photo(photo=movie['cover_image'])

            # Invia il messaggio di caricamento
            loading_message = await update.message.reply_text("Caricamento film in corso, attendi....")

            # Invia il video
            await update.message.reply_video(
              video=movie['movie_file']
            )

            # Elimina il messaggio di caricamento
            await loading_message.delete()
        else:
            await update.message.reply_text(f"Il film '{movie_title}' non è stato trovato.")
    else:
        await update.message.reply_text("Per favore, fornisci il titolo del film da cercare.")

# Main del bot
def main():
    # Token del bot
    application = Application.builder().token("7425320981:AAFpvBTs67JDXkfXPUnLknMsX68n49AFKzQ").build()

    # Gestione della conversazione
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('upload', upload)],  # Modificato /start con /upload
        states={
            ASK_MOVIE: [MessageHandler(filters.Document.ALL, handle_movie)],
            ASK_TITLE: [MessageHandler(filters.TEXT, handle_title)],
            ASK_COVER: [MessageHandler(filters.PHOTO, handle_cover)],
            ASK_YEAR: [MessageHandler(filters.TEXT, handle_year)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Aggiungi il comando /cerca
    application.add_handler(CommandHandler("cerca", search))

    # Avvia il bot
    application.run_polling()

if __name__ == "__main__":
    main()
