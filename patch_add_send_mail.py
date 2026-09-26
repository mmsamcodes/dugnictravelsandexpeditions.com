from pathlib import Path
path = Path(r'c:\Users\slick\dugnictravelsandexpeditions.com\app.py')
text = path.read_text(encoding='utf-8')
needle = "    conn.commit()\n    conn.close()\n\n\n\ndef require_admin(view):\n"
insert = "    conn.commit()\n    conn.close()\n\n\ndef send_mail(subject, body, reply_to=None):\n    msg = EmailMessage()\n    msg['Subject'] = subject\n    msg['From'] = app.config['MAIL_DEFAULT_SENDER']\n    msg['To'] = app.config['MAIL_RECIPIENT']\n    if reply_to:\n        msg['Reply-To'] = reply_to\n    msg.set_content(body)\n\n    server_host = app.config['MAIL_SERVER']\n    server_port = app.config['MAIL_PORT']\n    use_ssl = app.config['MAIL_USE_SSL']\n    use_tls = app.config['MAIL_USE_TLS']\n    username = app.config['MAIL_USERNAME']\n    password = app.config['MAIL_PASSWORD']\n\n    if use_ssl:\n        server = smtplib.SMTP_SSL(server_host, server_port, timeout=30)\n    else:\n        server = smtplib.SMTP(server_host, server_port, timeout=30)\n        server.ehlo()\n        if use_tls:\n            server.starttls()\n            server.ehlo()\n\n    try:\n        if username and password:\n            server.login(username, password)\n        server.send_message(msg)\n    finally:\n        server.quit()\n\n\ndef require_admin(view):\n"
if needle not in text:
    raise SystemExit('needle not found for send_mail insertion')
text = text.replace(needle, insert, 1)
path.write_text(text, encoding='utf-8')
print('patched app.py with send_mail helper')
