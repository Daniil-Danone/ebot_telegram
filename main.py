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
caption = ''


@bot.message_handler(content_types=['text', 'photo'])
def listener(message):
    con = sqlite3.connect('users.db')
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(user_id INT PRIMARY KEY, name TEXT, email TEXT, flag TEXT);""")
    con.commit()
    cur.close()

    if message.text == '/start':
        if user_exists(message.from_user.id) is None:
            user_id = message.from_user.id

            con = sqlite3.connect('users.db')
            cur = con.cursor()

            insert = '''INSERT INTO users (user_id, flag) VALUES(?, ?);'''
            data = (user_id, 'name', )

            cur.execute(insert, data)
            con.commit()
            cur.close()

            text = bot.send_message(message.chat.id, "Как Вас зовут?")
            bot.register_next_step_handler(text, registration_name)

        else:
            bot.send_message(message.chat.id,
                             "Привет! Я EBot и готов к работе! Присылай сообщения и я перенаправлю их на твою почту")

    else:
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

                bot.send_message(message.from_user.id, "Письмо отправлено на почту ✅")

            else:
                bot.send_message(message.from_user.id, "Жду следующего сообщения...")

        elif message.content_type == 'photo':
            global count, media_id, caption

            if media_id == message.media_group_id:
                count += 1

            if message.media_group_id:
                media_id = message.media_group_id

            if message.caption:
                caption = message.caption

            file = bot.get_file(message.photo[-1].file_id)
            filename, file_exstension = os.path.splitext(file.file_path)

            downloaded_file = bot.download_file(file.file_path)
            src = 'files/' + str(message.photo[-1].file_id) + file_exstension

            with open(src, 'wb') as f:
                f.write(downloaded_file)

            link = upload(src, str(message.photo[-1].file_id) + file_exstension)

            if link:
                os.remove(src)
                links.append(link)
                bot.send_message(message.from_user.id, "Этот файл скачан на Google Drive\n\n"
                                                       f"Ссылка на файл: {link}")

            if len(links) == count:
                media_id = 0
                count = 0
                send_email(message, caption)

        else:
            bot.send_message(message.from_user.id, f"Тип файла: {message.content_type}")


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


def send_email(message, caption):
    global links

    time.sleep(20)

    try:
        chat, sender = '', ''

        if message.forward_from:
            chat, sender = forward_from(message)

        #  канал
        elif message.forward_from_chat:
            chat, sender = forward_from_chat(message)

        converted_time = lambda x: time.strftime("%d.%M.%Y %H:%M:%S", time.localtime(x))

        link_list = ''
        print(links)

        for i in links:
            link_list += f'<p>{i}</p>'

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
                                <i>{link_list}</i>
                                '''

        email = get_user_email(message.from_user.id)[0]

        mail_send(text, email)

        links = []

        bot.send_message(message.from_user.id, "Письмо отправлено на почту ✅")

    except Exception:
        bot.send_message(message.from_user.id, "Произошла ошибка при отправке письма")


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
