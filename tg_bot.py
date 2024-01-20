import sqlite3
from telegram import Update
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Создаем подключение к SQLite базе данных
conn = sqlite3.connect('events.db')
cursor = conn.cursor()

# Создаем таблицу для хранения данных о мероприятиях
cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        chat_id INTEGER,
        event_key TEXT,
        participants TEXT,
        PRIMARY KEY (chat_id, event_key)
    )
''')
conn.commit()


# Обработчик команды /event
def start_event(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    args = context.args
    event_key = " ".join(args)

    # Create a new SQLite connection and cursor specific to this thread
    conn_thread = sqlite3.connect('events.db')
    cursor_thread = conn_thread.cursor()

    cursor_thread.execute(
        'SELECT * FROM events WHERE chat_id=? AND event_key=?',
        (chat_id, event_key))
    existing_event = cursor_thread.fetchone()

    if not existing_event:
        cursor_thread.execute(
            'INSERT INTO events (chat_id, event_key, participants) VALUES (?, ?, ?)',
            (chat_id, event_key, ''))
        conn_thread.commit()

    cursor_thread.execute(
        'SELECT * FROM events WHERE chat_id=? AND event_key=?',
        (chat_id, event_key))
    event_data = cursor_thread.fetchone()

    # Close the connection specific to this thread
    conn_thread.close()

    # Отправляем сообщение с информацией о мероприятии и кнопками
    message_text = f"{event_key}\n\nУчастники: {event_data[2]}"
    keyboard = [[
        InlineKeyboardButton("Записаться", callback_data=f"join:{event_key}")
    ], [
        InlineKeyboardButton("Отказаться", callback_data=f"leave:{event_key}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(message_text, reply_markup=reply_markup)


def button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    user = f"@{query.from_user.username}"

    action, event_key = query.data.split(":")

    # Create a new SQLite connection and cursor specific to this thread
    conn_thread = sqlite3.connect('events.db')
    cursor_thread = conn_thread.cursor()

    cursor_thread.execute(
        'SELECT * FROM events WHERE chat_id=? AND event_key=?',
        (chat_id, event_key))
    event_data = cursor_thread.fetchone()

    # Initialize new_participants outside the if conditions
    new_participants = event_data[2].split(',')

    if action == "join":
        if user not in event_data[2]:
            new_participants.append(user)
            # Update the record in the database
            cursor_thread.execute(
                'UPDATE events SET participants=? WHERE chat_id=? AND event_key=?',
                (','.join(new_participants), chat_id, event_key))
            conn_thread.commit()

            # Send a new message when someone joins
            context.bot.send_message(
                chat_id,
                f"Участник {user} записался на {event_key}",
                reply_to_message_id=query.message.message_id)
    elif action == "leave":
        if user in event_data[2]:
            new_participants.remove(user)
            # Update the record in the database
            cursor_thread.execute(
                'UPDATE events SET participants=? WHERE chat_id=? AND event_key=?',
                (','.join(new_participants), chat_id, event_key))
            conn_thread.commit()

            # Send a message when someone leaves
            context.bot.send_message(
                chat_id,
                f"Участник {user} отказался от записи на {event_key}",
                reply_to_message_id=query.message.message_id)

    # Update the message_text with the new participant list
    # {', '.join(new_participants[1:])}
    new_message_text = f"{event_key}\n\nУчастники: "
    for i in range(1, len(new_participants)):
        new_message_text += '\n' + str(i) + '. ' + new_participants[i]

    try:
        context.bot.edit_message_text(new_message_text,
                                      chat_id=chat_id,
                                      message_id=query.message.message_id,
                                      reply_markup=query.message.reply_markup)
    except:
        pass
    # Close the connection specific to this thread
    conn_thread.close()


def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    bot_token = '6765245441:AAHgAq-VneFJGai-yUAbTJTOgGbRlXm8X-A'
    updater = Updater(bot_token)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("event", start_event))
    dp.add_handler(
        MessageHandler(Filters.text & ~Filters.update.edited_message,
                       start_event))
    dp.add_handler(CallbackQueryHandler(button_click))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
