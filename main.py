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

logging.basicConfig(
    filename="execution.log", level=logging.DEBUG, format="%(asctime)s %(message)s"
)


def email_is_from_today(message: Message) -> bool:
    received_time = email.utils.parsedate_tz(message["Date"])
    received_time_utc = datetime.fromtimestamp(email.utils.mktime_tz(received_time))
    return received_time_utc.date() == datetime.today().date()


def get_imap_session(imap_email:str, imap_password:str, imap_host:str) -> imaplib.IMAP4_SSL:
    logging.info("Logging into IMAP")
    imap = imaplib.IMAP4_SSL(imap_host)
    imap.login(imap_email, imap_password)
    return imap


def get_latest_email(imap_session: imaplib.IMAP4_SSL) -> Message:
    status, messages = imap_session.select("Matt")
    latest_email_id = int(messages[0])
    logging.info("Fetching latest email")
    res, message = imap_session.fetch(str(latest_email_id), "(RFC822)")

    for response in message:
        if isinstance(response, tuple):
            return email.message_from_bytes(response[1])


def get_email_body(message: Message, imap_session: imaplib.IMAP4_SSL) -> str:
    for part in message.walk():
        content_type = part.get_content_type()
        body = part.get_payload(decode=True)
        if body:
            body = body.decode()
        if content_type == "text/html":
            imap_session.close()
            imap_session.logout()
            return body


def format_text(text: str) -> str:
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    logging.info("Formatting to markdown")
    markdown = text_maker.handle(text)
    logging.info("Stripping header from markdown")
    start_index = markdown.find("##")
    markdown_formatted = markdown[start_index:]
    logging.info("Converting to rtf with pandoc")
    rtf = pypandoc.convert_text(
        markdown_formatted, "rtf", format="md", extra_args=["-s"]
    )
    logging.info("Adjusting indentation")
    rtf_formatted = rtf.replace("li720", "li250")
    return rtf_formatted


def generate_filepath() -> str:
    date_string = datetime.today().strftime("%d-%m-%Y")
    directory = "files"
    filepath = f"{directory}/Money Stuff {date_string}.rtf"
    return filepath


def file_exists(filepath: str) -> bool:
    return os.path.exists(filepath)


def write_to_rtf(text: str, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    logging.info(f"Writing to {filepath}")
    with open(filepath, "w") as f:
        f.write(text)


def send_to_kindle(filepath: str) -> None:
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
    logging.info("Opening SMTP connection")
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(config.smpt_server, 465, context=context) as server:
        logging.info("Logging in to SMTP")
        server.login(sender_email, password)
        logging.info("Sending email")
        server.sendmail(sender_email, kindle_email, text)


if __name__ == "__main__":
    imap_session = get_imap_session(
        imap_email=sender_email, imap_password=password, imap_host=imap_host_name
    )
    latest_email = get_latest_email(imap_session)
    today_filepath = generate_filepath()
    if not file_exists(today_filepath) and email_is_from_today(latest_email):
        email_body = get_email_body(latest_email, imap_session)
        formatted_text = format_text(email_body)
        target_filepath = generate_filepath()
        write_to_rtf(formatted_text, today_filepath)
        try:
            send_to_kindle(today_filepath)
            logging.info("Email sent to kindle")
        except Exception as e:
            os.remove(today_filepath)
            logging.error(e)

    else:
        logging.info("Newsletter has already been fetched today")
