import smtplib
from email.message import EmailMessage
import mimetypes
import os


def send_email(receiver_email,subject,body,attachment_csv=None, attachement_png = None):

    SMTP_SERVER = "ssl0.ovh.net"
    SMTP_PORT = 465

    SENDER_EMAIL = "mathieu.grossin@halcyon-performance.com"
    SENDER_PASSWORD = "XXXXXX"

    # Vérifiaction mail correct

    print("[mail_sender] Début envoie mail")

    try:

        # Création du mail
        msg = EmailMessage()

        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email

        msg.set_content(body)

        # Ajout des pi�ces jointes
        attachments = [attachment_csv, attachement_png]

        for filepath in attachments:

            if filepath is None:
                continue

            if not os.path.exists(filepath):
                continue

            mime_type, _ = mimetypes.guess_type(filepath)

            if mime_type is None:
                mime_type = "application/octet-stream"

            mime_main, mime_sub = mime_type.split("/")

            with open(filepath, "rb") as f:

                msg.add_attachment(
                    f.read(),
                    maintype=mime_main,
                    subtype=mime_sub,
                    filename=os.path.basename(filepath)
                )

        # Connexion SMTP
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:

            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)

            smtp.send_message(msg)

        print('[mail_sender] fin envoie mail')

        return 1

    except Exception as e:
        print(e)
        print('[mail_sender] envoie mail fail')
        return 0