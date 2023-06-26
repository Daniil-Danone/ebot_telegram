import os
import sqlite3
import telebot, time
from send_email import mail_send
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

TOKEN = os.environ.get("TOKEN")
BOT = telebot.TeleBot(TOKEN)


@BOT.message_handler(content_types=['text'])
def listener(message):
    con = sqlite3.connect('users.db')
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(id INT PRIMARY KEY, name TEXT, email TEXT, flag TEXT);""")
    con.commit()

    if message.text == '/start':
        text = 'Привет, меня зовут EBot.'
        BOT.send_message(message.from_user.id, text)

        if user_exists(cur, message.from_user.id) is None:
            insert_user(cur, con, message.from_user.id)
            BOT.send_message(message.from_user.id, "Давай начнём со знакомства. Как я могу к тебе обращаться?")
            set_flag(cur, con, message.from_user.id, 'name')

        else:
            BOT.send_message(message.from_user.id,
                             "Ты уже зарегистрирован, можешь начинать работать со мной прямо сейчас 😃")
    else:
        if get_flag(cur, message.from_user.id)[0] == 'name':
            set_name(cur, con, message.text, message.from_user.id)
            BOT.send_message(message.from_user.id, "Отправь свою почту")
            set_flag(cur, con, message.from_user.id, 'email')

        elif get_flag(cur, message.from_user.id)[0] == 'email':
            set_email(cur, con, message.text, message.from_user.id)
            set_flag(cur, con, message.from_user.id, 'registered')
            BOT.send_message(message.from_user.id,
                             "Регистрация завершена, можешь начинать работать со мной прямо сейчас 😃")

        elif get_flag(cur, message.from_user.id)[0] == 'registered':
            email = get_email(cur, message.from_user.id)[0]

            #  чаты
            if message.forward_from:
                chat = message.chat.first_name
                print("A", message.forward_from)

                name = message.forward_from.first_name
                surname = message.forward_from.last_name
                username = message.forward_from.username
                if surname:
                    name += ' '
                # else:
                    surname = ''
                sender = name + surname + f' (@{username})'

            #  канал
            elif message.forward_from_chat:
                data = message.forward_from_chat
                print("B", message.forward_from_chat)

                chat = data.title
                if message.forward_signature is None:
                    sender = "Аноним 🦹"
                else:
                    sender = message.forward_signature

            else:
                return

            tconv = lambda x: time.strftime("%d.%M.%Y %H:%M:%S", time.localtime(x))

            text = f'''
            <p>Вы отметили данное сообщение как <b>важное</b></p>
            <p>Чат: {chat}</p>
            <p>Отправитель: {sender}</p>
            <p>Время написания: {tconv(message.forward_date)}</p>
            <u>Оригинальное сообщение:</u>
            <br>
            <i>{message.text}</i>
            '''

            print(text)

            mail_send(text, email)
            BOT.send_message(message.from_user.id, "Письмо отправлено на почту ✅")


@BOT.message_handler(content_types=['photo'])
def photo_listener(message):
    print(message)
    file_photo = BOT.get_file(message.photo[-1].file_id)
    filename, file_exstension = os.path.splitext(file_photo.file_path)
    downloaded_photo = BOT.download_file(file_photo.file_path)
    src = 'photos/' + 'dfgdgd' + file_exstension

    with open(src, 'wb') as photo:
        photo.write(downloaded_photo)


def user_exists(cur, user_id):
    return cur.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()


def insert_user(cur, con, user_id):
    insert = '''INSERT INTO users (id) VALUES(?);'''
    data = (user_id,)
    cur.execute(insert, data)
    con.commit()


def set_name(cur, con, message, user_id):
    insert = '''UPDATE users SET name = ? WHERE id = ?;'''
    data = (message, user_id, )
    cur.execute(insert, data)
    con.commit()


def set_email(cur, con, message, user_id):
    insert = '''UPDATE users SET email = ? WHERE id = ?'''
    data = (message, user_id, )
    cur.execute(insert, data)
    con.commit()


def set_flag(cur, con, user_id, value):
    insert = '''UPDATE users SET flag = ? WHERE id = ?'''
    data = (value, user_id,)
    cur.execute(insert, data)
    con.commit()


def get_flag(cur, user_id):
    return cur.execute('SELECT flag FROM users WHERE id=?', (user_id,)).fetchone()


def get_email(cur, user_id):
    return cur.execute('SELECT email FROM users WHERE id=?', (user_id,)).fetchone()


BOT.polling(none_stop=True, interval=0)
