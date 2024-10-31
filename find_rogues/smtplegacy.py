import smtplib
import yaml
from rich import print
from email.message import EmailMessage

with open(".env.yaml", "r") as envf:
    central_info = yaml.safe_load(envf)


def send_legacy_email(table, account="default"):
    # Create EmailMessage object
    message = EmailMessage()
    message.set_content(table)
    message["Subject"] = (central_info[account]["subject"])
    message["From"] = (central_info[account]["from_email"])
    message["To"] = (central_info[account]["to_emails"][0])

    # Create SMTP Session and send message
    session = smtplib.SMTP_SSL(
        central_info[account]["smtp"]["host"], central_info[account]["smtp"]["port"]
    )
    session.login(
        central_info[account]["smtp"]["username"],
        central_info[account]["smtp"]["password"],
    )
    session.send_message(message)
