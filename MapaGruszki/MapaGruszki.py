from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from queue import Queue

AREA_BOUNDARIES = {
    "min_lat": 54.30,
    "max_lat": 54.60,
    "min_lon": 18.40,
    "max_lon": 18.85,
}

user_locations = {}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Witaj! Kliknij przycisk poniżej, aby oznaczyć miejsce paczki na mapie.\n"
        "Mapa działa tylko na terenie Gdyni, Gdańska i Sopotu.\n\n"
        "Kliknij przycisk poniżej, aby udostępnić swoją lokalizację.",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("Udostępnij lokalizację", request_location=True)]
        ], one_time_keyboard=True)
    )

def handle_location(update: Update, context: CallbackContext) -> None:
    user_location = update.message.location
    latitude = user_location.latitude
    longitude = user_location.longitude

    user_id = update.message.from_user.id
    user_locations[user_id] = (latitude, longitude)

    if (
        AREA_BOUNDARIES["min_lat"] <= latitude <= AREA_BOUNDARIES["max_lat"]
        and AREA_BOUNDARIES["min_lon"] <= longitude <= AREA_BOUNDARIES["max_lon"]
    ):
        update.message.reply_text(
            f"Dziękuję! Twoja lokalizacja została zapisana.\n"
            f"📍 Szerokość: {latitude}\n"f"📍 Długość: {longitude}\n"
            "Możesz teraz otworzyć mapę, która wyświetli się w Twojej lokalizacji.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Otwórz mapę", callback_data="mapa")]
            ])
        )
    else:
        update.message.reply_text(
            "Twoja lokalizacja została zapisana, ale znajduje się poza obsługiwanym obszarem (Gdynia, Gdańsk, Sopot).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Otwórz mapę", callback_data="mapa")]
            ])
        )

def show_map(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    if user_id in user_locations:
        latitude, longitude = user_locations[user_id]
    else:
        latitude = 54.45
        longitude = 18.60

    query.message.reply_location(
        latitude=latitude,
        longitude=longitude,
        live_period=None,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Zaznacz paczkę tutaj", callback_data=f"mark|{latitude}|{longitude}")]
        ])
    )
    query.edit_message_text("Zaznacz aktualne położenie twojej paczki, stój w tym samym miejscu co paczka!!")

def request_photo(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    query.message.reply_text(
        "Proszę teraz przesłać zdjęcie paczki.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Prześlij zdjęcie paczki", callback_data="send_photo")]
        ])
    )

def handle_photo(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_locations:
        update.message.reply_text("Najpierw oznacz lokalizację paczki.")
        return

    photo_file = update.message.photo[-1].get_file()
    photo_path = f'paczka_{user_id}.jpg'
    photo_file.download(photo_path)

    latitude, longitude = user_locations[user_id]

    update.message.reply_text(
        f"Dziękujemy za przesłanie zdjęcia paczki!\n"
        f"📍 Szerokość: {latitude}\n"
        f"📍 Długość: {longitude}\n"
        "Zdjęcie paczki zostało zapisane."
    )

    context.bot.send_photo(
        chat_id=update.message.chat_id,
        photo=open(photo_path, 'rb'),
        caption=f"📍 Szerokość: {latitude}\n📍 Długość: {longitude}"
    )

def confirm_marker(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    try:
        data = query.data.split("|")
        if len(data) != 3 or data[0] != "mark":
            raise ValueError("Nieprawidłowe dane callback_data.")
        
        latitude = float(data[1])
        longitude = float(data[2])

    except (ValueError, IndexError) as e:
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Błąd: Nieprawidłowe dane lub współrzędne. Upewnij się, że zaznaczenie zostało wykonane poprawnie."
        )
        return

    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            f"Paczka została oznaczona pod współrzędnymi:\n"
            f"📍 Szerokość: {latitude}\n"
            f"📍 Długość: {longitude}\n"
            "Dziękujemy za użycie bota! Proszę teraz przesłać zdjęcie paczki."
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Prześlij zdjęcie paczki", callback_data="send_photo")]
        ])
    )

def main():
    TOKEN = "BOTTOKENHERE"
    update_queue = Queue()

    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(show_map, pattern="^mapa$"))
    dispatcher.add_handler(CallbackQueryHandler(confirm_marker, pattern="^mark\\|.*"))
    dispatcher.add_handler(CallbackQueryHandler(request_photo, pattern="^send_photo$"))
    dispatcher.add_handler(MessageHandler(Filters.location, handle_location))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))


    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
