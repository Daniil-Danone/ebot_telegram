import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv, find_dotenv
from email.mime.multipart import MIMEMultipart


load_dotenv(find_dotenv())
EMAIL = os.environ.get('EMAIL')
PASSWORD = os.environ.get('PASSWORD')
print(EMAIL, PASSWORD)


def mail_send(text, address):
    print(text, address)
    html = f"""
        <html>
        <head></head>
        <body>
            <p>{text}</p>
        </body>
        </html>
        """
    text = "Важное!"

    message = MIMEMultipart('alternative')
    message['Subject'] = "Link"
    message['From'] = EMAIL
    message['To'] = address

    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    message.attach(part1)
    message.attach(part2)

    mail = smtplib.SMTP('smtp.yandex.ru', 587)
    mail.ehlo()
    mail.starttls()
    mail.ehlo()
    mail.login(EMAIL, PASSWORD)

    mail.sendmail(EMAIL, address, message.as_string())
    mail.quit()
