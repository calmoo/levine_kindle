import imaplib
import email
import imaplib
import logging
import os
import os.path
import smtplib
import ssl
from datetime import datetime
from email import encoders, utils
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import html2text
import pypandoc

import config

sender_email = config.email_account
kindle_email = config.kindle_email
password = config.email_password
imap_host_name = config.imap_host


def email_is_from_today(message):
    received_time = email.utils.parsedate_tz(message['Date'])
    received_time_utc = datetime.fromtimestamp(email.utils.mktime_tz(received_time))
    return received_time_utc.date() == datetime.today().date()


def get_imap_session(imap_email, imap_password, imap_host):
    print("Logging into IMAP")
    imap = imaplib.IMAP4_SSL(imap_host)
    imap.login(imap_email, imap_password)
    return imap


def get_latest_email(imap_session):
    status, messages = imap_session.select("Matt")
    latest_email_id = int(messages[0])
    print("Fetching latest email")
    res, message = imap_session.fetch(str(latest_email_id), "(RFC822)")

    for response in message:
        if isinstance(response, tuple):
            return email.message_from_bytes(response[1])


def get_email_body(message, imap_session):
    for part in message.walk():
        content_type = part.get_content_type()
        body = part.get_payload(decode=True)
        if body:
            body = body.decode()
        if content_type == "text/html":
            imap_session.close()
            imap_session.logout()
            return body


def format_text(text):
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    print("Formatting to markdown")
    markdown = text_maker.handle(text)
    print("Stripping header from markdown")
    start_index = markdown.find("##")
    markdown_formatted = markdown[start_index:]
    print("Converting to rtf with pandoc")
    rtf = pypandoc.convert_text(
        markdown_formatted, "rtf", format="md", extra_args=["-s"]
    )
    print("Adjusting indentation")
    rtf_formatted = rtf.replace("li720", "li250")
    return rtf_formatted


def generate_filepath():
    date_string = datetime.today().strftime("%d-%m-%Y")
    directory = "files"
    filepath = f"{directory}/Money Stuff {date_string}.rtf"
    return filepath


def file_exists(filepath):
    return os.path.exists(filepath)


def write_to_rtf(text, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    print(f"Writing to {filepath}")
    with open(filepath, "w") as f:
        f.write(text)
    return filepath


def send_to_kindle(filepath):
    subject = "Kindle Automation"
    body = "Newsletter"
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = kindle_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    with open(filepath, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    filename = filepath.split("/")[1]
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {filename}",
    )
    message.attach(part)
    text = message.as_string()
    print("Opening SMTP connection")
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(config.smpt_server, 465, context=context) as server:
        print("Logging in to SMTP")
        server.login(sender_email, password)
        print("Sending email")
        server.sendmail(sender_email, "test@test.com", text)


if __name__ == "__main__":
    if not file_exists(generate_filepath()):
        imap_session = get_imap_session(imap_email=sender_email, imap_password=password, imap_host=imap_host_name)
        latest_email = get_latest_email(imap_session)
        if email_is_from_today(latest_email):
            email_body = get_email_body(latest_email, imap_session)
            formatted_text = format_text(email_body)
            rtf_filepath = write_to_rtf(formatted_text, generate_filepath())
            try:
                send_to_kindle(rtf_filepath)
                print("Email sent to kindle")
            except:
                os.remove(rtf_filepath)
                print("Unable to send to kindle, deleted file")
    else:
        print("Newsletter has already been fetched today")
