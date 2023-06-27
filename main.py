import os
import time
import sqlite3
import telebot
from send_email import mail_send
from google_disk import upload
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN)

msg_id = 0
links = []

count = 0
media_id = 0


@bot.message_handler(content_types=['text'])
def welcome(message):
    con = sqlite3.connect('users.db')
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(user_id INT PRIMARY KEY, name TEXT, email TEXT, flag TEXT);""")
    con.commit()
    cur.close()

    if user_exists(message.from_user.id):
        text = bot.send_message(message.chat.id,
                                "Привет! Я EBot и готов к работе! Присылай сообщения и я перенаправлю их на твою почту")
        bot.register_next_step_handler(text, listener)

    if message.text == '/start':
        text = 'Привет, меня зовут EBot.'
        bot.send_message(message.from_user.id, text)

        if user_exists(message.from_user.id) is None:
            user_id = message.from_user.id

            con = sqlite3.connect('users.db')
            cur = con.cursor()

            insert = '''INSERT INTO users (user_id, flag) VALUES(?, ?);'''
            data = (user_id, 'name',)

            cur.execute(insert, data)
            con.commit()
            cur.close()

            text = bot.send_message(message.chat.id, "Как Вас зовут?")
            bot.register_next_step_handler(text, registration_name)


@bot.message_handler(content_types=['text', 'photo'])
def listener(message):
    if message.content_type == 'text':
        if message.forward_from or message.forward_from_chat:

            chat, sender = '', ''

            if message.forward_from:
                chat, sender = forward_from(message)

            #  канал
            elif message.forward_from_chat:
                chat, sender = forward_from_chat(message)

            converted_time = lambda x: time.strftime("%d.%M.%Y %H:%M:%S", time.localtime(x))

            text = f'''<b>ВАЖНОЕ - Вы отметили данное сообщение</b>
            <p><b>Чат:</b> <i>{chat}</i></p>
            <p><b>Отправитель:</b> <i>{sender}</i></p>
            <p><b>Время написания:</b> <i>{converted_time(message.forward_date)}</i></p>
            <b>Оригинальное сообщение:</b>
            <br>
            <i>{message.text}</i>
            '''

            email = get_user_email(message.from_user.id)[0]

            mail_send(text, email)

            text = bot.reply_to(message, "Письмо отправлено на почту ✅")
            bot.register_next_step_handler(text, listener)

        else:
            text = bot.reply_to(message, "Жду следующего сообщения...")
            bot.register_next_step_handler(text, listener)

    elif message.content_type == 'photo':
        global count, media_id

        if media_id == message.media_group_id:
            count += 1

        if message.media_group_id:
            media_id = message.media_group_id

        file = bot.get_file(message.photo[-1].file_id)
        filename, file_exstension = os.path.splitext(file.file_path)

        downloaded_file = bot.download_file(file.file_path)
        src = 'files/' + str(message.photo[-1].file_id) + file_exstension

        with open(src, 'wb') as f:
            f.write(downloaded_file)

        link = upload(src, str(message.photo[-1].file_id) + file_exstension)

        if link:
            links.append(link)
            text = bot.reply_to(message, "Этот файл скачан на Google Drive\n\n"
                                         f"Ссылка на файл: {link}")
            bot.register_next_step_handler(text, listener)

        if len(links) == count:
            print('ok-')

    else:
        text = bot.send_message(message.chat.id, f"Тип файла: {message.content_type}")
        bot.register_next_step_handler(text, listener)


def user_exists(user_id):
    con = sqlite3.connect('users.db')
    cur = con.cursor()
    return cur.execute('SELECT * FROM users WHERE user_id=?', (user_id,)).fetchone()


def registration_name(message):
    user_id = message.from_user.id
    name = message.text

    con = sqlite3.connect('users.db')
    cur = con.cursor()

    insert = '''UPDATE users SET name = ?, flag = ? WHERE user_id = ?;'''
    data = (name, 'email', user_id)

    cur.execute(insert, data)
    con.commit()
    cur.close()

    text = bot.send_message(message.chat.id, "На какую почту Вы бы хотели получать письма?")
    bot.register_next_step_handler(text, registration_email)


def registration_email(message):
    user_id = message.from_user.id
    email = message.text

    con = sqlite3.connect('users.db')
    cur = con.cursor()

    insert = '''UPDATE users SET email = ?, flag = ? WHERE user_id = ?;'''
    data = (email, 'registred', user_id)

    cur.execute(insert, data)
    con.commit()
    cur.close()

    text = bot.send_message(message.chat.id, "Регистрация окончена!")
    bot.register_next_step_handler(text, listener)


def get_user_email(user_id):
    con = sqlite3.connect('users.db')
    cur = con.cursor()
    return cur.execute('SELECT email FROM users WHERE user_id=?', (user_id,)).fetchone()


def forward_from(message):
    chat = message.chat.first_name
    name = message.forward_from.first_name
    username = message.forward_from.username
    sender = name + f' (@{username})'

    return chat, sender


def forward_from_chat(message):
    chat = message.forward_from_chat.title

    if message.forward_signature is None:
        sender = "Аноним 🦹"
    else:
        sender = message.forward_signature

    return chat, sender


def send_email(message):
    global links

    try:
        caption = message.caption

        chat, sender = '', ''

        if message.forward_from:
            chat, sender = forward_from(message)

        #  канал
        elif message.forward_from_chat:
            chat, sender = forward_from_chat(message)

        converted_time = lambda x: time.strftime("%d.%M.%Y %H:%M:%S", time.localtime(x))

        text = f'''<b>ВАЖНОЕ - Вы отметили данное сообщение</b>
                                <p><b>Чат:</b> <i>{chat}</i></p>
                                <p><b>Отправитель:</b> <i>{sender}</i></p>
                                <p><b>Время написания:</b> <i>{converted_time(message.forward_date)}</i></p>
                                <b>Оригинальное сообщение:</b>
                                <br>
                                <i>{caption}</i>
                                <br>
                                <b>Вложения:</b>
                                <br>
                                <i>{links}</i>
                                '''

        email = get_user_email(message.from_user.id)[0]

        mail_send(text, email)

        links = []

        text = bot.reply_to(message, "Письмо отправлено на почту ✅")
        bot.register_next_step_handler(text, listener)

    except Exception:
        text = bot.send_message(message.chat.id, "Произошла ошибка при отправке письма")
        bot.register_next_step_handler(text, listener)


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)

