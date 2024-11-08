import smtplib
import yaml
# from rich import print
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart

from email.mime.text import MIMEText

with open(".env.yaml", "rb") as envf:
    central_info = yaml.safe_load(envf)


def send_legacy_email(table, account="default", html=True):
    # Create EmailMessage object
    if html:
        message = MIMEMultipart("alternative")
        # message.set_content(table, subtype="html")
        part1 = MIMEText(table, "html")
        message.attach(part1)
    else:
        message = EmailMessage()
        message.set_content(table)

    message["Subject"] = central_info[account]["subject"]
    message["From"] = central_info[account]["from_email"]
    message["To"] = central_info[account]["to_emails"][0]

    # Create SMTP Session and send message
    # session = smtplib.SMTP_SSL(
    # # session = smtplib.SMTP(
    #     central_info[account]["smtp"]["host"], central_info[account]["smtp"]["port"]
    # )
    # session.starttls()
    # session.login(
    #     central_info[account]["smtp"]["username"],
    #     central_info[account]["smtp"]["password"],
    # )
    # session.send_message(message)
    with smtplib.SMTP(
        central_info[account]["smtp"]["host"], central_info[account]["smtp"]["port"]
    ) as session:
        # session.starttls()
        # session.login(
        #     central_info[account]["smtp"]["username"],
        #     central_info[account]["smtp"]["password"],
        # )
        session.send_message(message)
