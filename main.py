import imaplib
import email
import os
import os.path

import html2text
import pypandoc
from datetime import datetime

import smtplib
import ssl
import config
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sender_email = config.email_account
kindle_email = config.kindle_email
password = config.email_password


def get_email_body():
    print("Logging into IMAP")
    imap = imaplib.IMAP4_SSL(config.imap_host)
    imap.login(sender_email, password)
    status, messages = imap.select("Matt")
    latest_email_id = int(messages[0])
    print("Fetching latest email")
    res, msg = imap.fetch(str(latest_email_id), "(RFC822)")

    for response in msg:
        if isinstance(response, tuple):
            msg = email.message_from_bytes(response[1])
            for part in msg.walk():
                content_type = part.get_content_type()
                body = part.get_payload(decode=True)
                if body:
                    body = body.decode()
                if content_type == "text/html":
                    imap.close()
                    imap.logout()
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
        server.sendmaail(sender_email, kindle_email, text)


if __name__ == "__main__":
    if not file_exists(generate_filepath()):
        email_text = get_email_body()
        formatted_text = format_text(email_text)
        rtf_filepath = write_to_rtf(formatted_text, generate_filepath())
        try:
            send_to_kindle(rtf_filepath)
            print("Email sent to kindle")
        except:
            os.remove(os.path.dirname(rtf_filepath))
            print("Unable to send to kindle, deleted file")
    else:
        print("Newsletter has already been fetched today")
