import os
import posixpath
import secrets
import sqlite3
import smtplib
import uuid
import json
from email.message import EmailMessage
from functools import wraps
from flask import Flask, abort, jsonify, redirect, render_template_string, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['DATABASE'] = os.environ.get(
    'DATABASE_PATH',
    os.path.join(os.path.dirname(__file__), 'blog.sqlite3'),
)
app.config['UPLOAD_FOLDER'] = os.environ.get(
    'UPLOAD_FOLDER',
    os.path.join(os.path.dirname(__file__), 'uploads'),
)
app.config['ADMIN_USERNAME'] = os.environ.get('ADMIN_USERNAME')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'mail.dugnictravelsandexpeditions.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '465'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'true').lower() in ('1', 'true', 'yes')
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'info@dugnictravelsandexpeditions.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'info@dugnictravelsandexpeditions.com')
app.config['MAIL_RECIPIENT'] = 'info@dugnictravelsandexpeditions.com'


def get_db():
    if not os.path.exists(app.config['DATABASE']):
        init_db()

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(app.config['DATABASE'])), exist_ok=True)
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT,
            date TEXT,
            excerpt TEXT,
            content TEXT NOT NULL,
            media_filename TEXT,
            media_type TEXT,
            media_items TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    post_columns = {
        column[1] for column in conn.execute('PRAGMA table_info(posts)')
    }
    if 'media_items' not in post_columns:
        conn.execute('ALTER TABLE posts ADD COLUMN media_items TEXT')
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        '''
    )
    username = (app.config.get('ADMIN_USERNAME') or '').strip()
    password = app.config.get('ADMIN_PASSWORD') or ''
    if bool(username) != bool(password):
        conn.close()
        raise RuntimeError('Set both ADMIN_USERNAME and ADMIN_PASSWORD to configure the admin account.')
    if username and password:
        conn.execute(
            '''
            INSERT INTO admin_users (id, username, password_hash)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                password_hash = excluded.password_hash
            ''',
            (username, generate_password_hash(password)),
        )
    conn.commit()
    conn.close()


init_db()


def send_mail(subject, body, reply_to=None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = app.config['MAIL_RECIPIENT']
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.set_content(body)

    server_host = app.config['MAIL_SERVER']
    server_port = app.config['MAIL_PORT']
    use_ssl = app.config['MAIL_USE_SSL']
    use_tls = app.config['MAIL_USE_TLS']
    username = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']

    if (use_ssl or use_tls) and not (username and password):
        raise RuntimeError('SMTP authentication is required for secure mail delivery.')

    if use_ssl:
        server = smtplib.SMTP_SSL(server_host, server_port, timeout=30)
    else:
        server = smtplib.SMTP(server_host, server_port, timeout=30)
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()

    try:
        if username and password:
            server.login(username, password)
        server.send_message(msg)
    finally:
        server.quit()


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin_user'):
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapped


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        admin = conn.execute(
            'SELECT username, password_hash FROM admin_users WHERE username = ?',
            (username,),
        ).fetchone()
        conn.close()
        if admin and check_password_hash(admin['password_hash'], password):
            session.clear()
            session['admin_user'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid username or password.'
        if not admin and not app.config.get('ADMIN_USERNAME'):
            error = 'Admin login is not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD on the server.'

    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Admin Login · Dugnic Travels</title>
          <link rel="icon" type="image/jpeg" href="/downloads/logo.jpeg" />
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
          <link href="https://fonts.googleapis.com/css2?family=Gilda+Display&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet" />
          <style>
            :root { --forest: #0f5a3e; --forest-deep: #083d2b; --gold: #c7922b; --cream: #f8f3e7; --ink: #172126; --muted: #53606a; --border: rgba(8,61,43,0.1); }
            * { box-sizing: border-box; }
            body { margin: 0; font-family: "Roboto", Arial, sans-serif; background: linear-gradient(135deg, var(--cream), #fffdf8); color: var(--ink); }
            .shell { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
            .card { width: min(460px, 100%); background: white; border-radius: 24px; padding: 30px; box-shadow: 0 20px 48px rgba(8, 61, 43, 0.12); border: 1px solid rgba(8,61,43,0.08); }
            h1, h2 { font-family: "Gilda Display", Georgia, serif; color: var(--forest-deep); margin: 0 0 10px; }
            p { color: var(--muted); }
            form { display: grid; gap: 12px; margin-top: 18px; }
            input, textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid #d8d0c0; font: inherit; }
            button { border: 0; cursor: pointer; padding: 12px 16px; border-radius: 999px; font-weight: 700; background: var(--gold); color: white; }
            .back-link { display: inline-block; margin-top: 14px; color: var(--forest); font-weight: 700; }
            .error { color: #a12622; font-weight: 700; }
          </style>
        </head>
        <body>
          <div class="shell">
            <div class="card">
              <div class="eyebrow">Private dashboard</div>
              <h1>Welcome back, admin</h1>
              <p>Use the dashboard to publish beautiful travel stories, upload media, and keep the homepage fresh.</p>
              {% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
              <form method="post">
                <input name="username" placeholder="Username" required />
                <input name="password" type="password" placeholder="Password" required />
                <button type="submit">Enter dashboard</button>
              </form>
              <a class="back-link" href="/">Return to the site</a>
            </div>
          </div>
        </body>
        </html>
    ''', error=error)


@app.route('/admin/dashboard')
@require_admin
def admin_dashboard():
    posts = get_posts()
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Admin Dashboard · Dugnic Travels</title>
          <link rel="icon" type="image/jpeg" href="/downloads/logo.jpeg" />
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
          <link href="https://fonts.googleapis.com/css2?family=Gilda+Display&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet" />
          <style>
            :root { --forest: #0f5a3e; --forest-deep: #083d2b; --gold: #c7922b; --cream: #f8f3e7; --ink: #172126; --muted: #53606a; --border: rgba(8,61,43,0.1); }
            * { box-sizing: border-box; }
            body { margin: 0; font-family: "Roboto", Arial, sans-serif; background: linear-gradient(135deg, var(--cream), #fffdf8); color: var(--ink); }
            .shell { max-width: 1180px; margin: 0 auto; padding: 24px; }
            .card { background: white; border: 1px solid var(--border); border-radius: 24px; padding: 24px; box-shadow: 0 20px 48px rgba(8,61,43,0.1); margin-bottom: 18px; }
            .shell { color: #172126; font-size: 16px; line-height: 1.6; }
            .shell .card p { color: #37444b; font-size: 1rem; line-height: 1.6; }
            .shell .post-item h3 { font-size: 1.3rem; line-height: 1.35; }
            .topbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 18px; }
            h1, h2, h3 { font-family: "Gilda Display", Georgia, serif; color: var(--forest-deep); margin: 0 0 10px; }
            p { color: var(--muted); }
            form { display: grid; gap: 12px; }
            input, textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid #d8d0c0; font: inherit; }
            input, textarea { color: #172126; background-color: #fff; }
            input::placeholder, textarea::placeholder { color: #59636b; opacity: 1; }
            textarea { min-height: 110px; resize: vertical; }
            button { border: 0; cursor: pointer; padding: 12px 16px; border-radius: 999px; font-weight: 700; background: var(--gold); color: white; }
            .secondary-link { color: var(--forest); font-weight: 700; }
            .grid { display: grid; gap: 18px; grid-template-columns: 1.1fr 0.9fr; }
            .post-item { padding: 12px 0; border-top: 1px solid rgba(8,61,43,0.08); }
            .post-item:first-child { border-top: 0; padding-top: 0; }
            .delete-form { display: inline-block; margin-top: 4px; }
            .delete-button { background: #a12622; }
            .shell .pill { color: #083d2b; font-size: 0.85rem; }
            .upload-help { margin: -4px 0 0; color: #4b565e; font-size: 0.92rem; }
            .pill { display: inline-block; padding: 4px 10px; background: rgba(15,90,62,0.08); color: var(--forest-deep); border-radius: 999px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }
            @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }
          </style>
        </head>
        <body>
          <div class="shell">
            <div class="topbar">
              <div>
                <h1>Content dashboard</h1>
                <p>Publish travel stories, add visuals, and keep the homepage feeling fresh.</p>
              </div>
              <form method="post" action="/admin/logout">
                <button type="submit">Log out</button>
              </form>
            </div>
            <div class="grid">
              <div class="card">
                <h2>Create a story</h2>
                <form method="post" action="/admin/posts" enctype="multipart/form-data">
                  <input name="title" placeholder="Story title" required />
                  <input name="category" placeholder="Category" required />
                  <input name="location" placeholder="Location" />
                  <input name="date" type="date" />
                  <textarea name="excerpt" placeholder="Short intro"></textarea>
                  <textarea name="content" placeholder="Full story" required></textarea>
                  <label for="post-media">Story photos and videos</label>
                  <input id="post-media" name="media" type="file" accept="image/*,video/*" multiple />
                  <p class="upload-help">Select one or more photos and videos. They will appear together in the story gallery.</p>
                  <button type="submit">Publish to homepage</button>
                </form>
              </div>
              <div class="card">
                <h2>Published stories</h2>
                {% for post in posts %}
                  <div class="post-item">
                    <span class="pill">{{ post.category }}</span>
                    <h3>{{ post.title }}</h3>
                    <p>{{ post.excerpt }}</p>
                    {% if post.media_items %}
                      <p>Gallery: {{ post.media_items|length }} item{% if post.media_items|length != 1 %}s{% endif %}</p>
                    {% endif %}
                    <form class="delete-form" method="post" action="{{ url_for('delete_post_route', post_id=post.id) }}" onsubmit="return confirm('Delete this story permanently?');">
                      <button class="delete-button" type="submit">Delete story</button>
                    </form>
                  </div>
                {% else %}
                  <p>No stories have been published yet.</p>
                {% endfor %}
              </div>
            </div>
          </div>
        </body>
        </html>
    ''', posts=posts)


@app.route('/admin/posts', methods=['POST'])
@require_admin
def create_post_route():
    title = request.form.get('title', '').strip()
    category = request.form.get('category', '').strip()
    location = request.form.get('location', '').strip()
    date = request.form.get('date', '').strip()
    excerpt = request.form.get('excerpt', '').strip()
    content = request.form.get('content', '').strip()

    uploads = [
        upload for upload in request.files.getlist('media')
        if upload and upload.filename
    ]
    validated_uploads = []
    for upload in uploads:
        filename = secure_filename(upload.filename)
        if not filename:
            abort(400, description='A media file has an invalid filename.')
        if upload.mimetype.startswith('image/'):
            media_type = 'image'
        elif upload.mimetype.startswith('video/'):
            media_type = 'video'
        else:
            abort(400, description='Only image and video files can be added to a story.')
        validated_uploads.append((upload, filename, media_type))

    media_items = []
    for upload, filename, media_type in validated_uploads:
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        upload.save(upload_path)
        media_items.append({'filename': unique_name, 'type': media_type})

    first_media = media_items[0] if media_items else None

    create_post(
        title=title,
        category=category,
        location=location,
        date=date,
        excerpt=excerpt,
        content=content,
        media_filename=first_media['filename'] if first_media else None,
        media_type=first_media['type'] if first_media else None,
        media_items=media_items,
    )
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@require_admin
def delete_post_route(post_id):
    conn = get_db()
    post = conn.execute(
        'SELECT media_filename, media_items FROM posts WHERE id = ?',
        (post_id,),
    ).fetchone()
    if post is None:
        conn.close()
        abort(404)

    try:
        media_items = json.loads(post['media_items']) if post['media_items'] else []
    except json.JSONDecodeError as exc:
        conn.close()
        raise RuntimeError(f'Invalid media gallery data for blog post {post_id}.') from exc

    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()

    media_filenames = {item['filename'] for item in media_items}
    if post['media_filename']:
        media_filenames.add(post['media_filename'])
    for media_filename in media_filenames:
        if secure_filename(media_filename) == media_filename:
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], media_filename)
            if os.path.isfile(media_path):
                os.remove(media_path)

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/posts')
def api_posts():
    return jsonify(get_posts())


@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/favicon.svg')
def favicon_svg():
    return send_from_directory(os.path.join(app.root_path, 'downloads'), 'logo.jpeg', mimetype='image/jpeg')


@app.route('/favicon.ico')
def favicon_ico():
    return send_from_directory(os.path.join(app.root_path, 'downloads'), 'logo.jpeg', mimetype='image/jpeg')


@app.route('/css/<path:filename>')
def css_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'css'), filename)


@app.route('/js/<path:filename>')
def js_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'js'), filename)


@app.route('/en')
@app.route('/en/')
@app.route('/en/index.html')
def en_home():
    return send_from_directory(app.root_path, 'index.html')


def normalize_route_path(path_value):
    safe_value = path_value.replace('\\', '/').lstrip('/')
    normalized = posixpath.normpath(safe_value)
    if normalized in ('', '.', '..') or normalized.startswith('../'):
        abort(404)
    return normalized


@app.route('/en/<path:path>')
def serve_en_pages(path):
    normalized_path = normalize_route_path(path)

    full_path = os.path.join(app.root_path, 'en', *normalized_path.split('/')) if normalized_path else os.path.join(app.root_path, 'en')
    if os.path.isfile(full_path):
        return send_from_directory(os.path.join(app.root_path, 'en'), normalized_path)
    if os.path.isdir(full_path):
        index_file = os.path.join(full_path, 'index.html')
        if os.path.isfile(index_file):
            return send_from_directory(full_path, 'index.html')
    abort(404)


@app.route('/<path:path>')
def serve_static(path):
    normalized_path = normalize_route_path(path)

    full_path = os.path.join(app.root_path, *normalized_path.split('/')) if normalized_path else app.root_path
    if os.path.isfile(full_path):
        return send_from_directory(app.root_path, normalized_path)
    if os.path.isdir(full_path):
        index_file = os.path.join(full_path, 'index.html')
        if os.path.isfile(index_file):
            return send_from_directory(full_path, 'index.html')
    abort(404)


def serve_static_page(relative_dir, filename='index.html'):
    directory = os.path.join(app.root_path, relative_dir)
    return send_from_directory(directory, filename)


@app.route('/tours')
@app.route('/tours/')
@app.route('/en/tours')
@app.route('/en/tours/')
@app.route('/en/tours/index.html')
def tours():
    return serve_static_page(os.path.join('en', 'tours'))


@app.route('/contact')
@app.route('/contact/')
@app.route('/en/Contact')
@app.route('/en/Contact/')
@app.route('/en/Contact/index.html')
def contact():
    return serve_static_page(os.path.join('en', 'Contact'))


@app.route('/contact/submit', methods=['POST'])
@app.route('/en/Contact/submit', methods=['POST'])
def contact_submit():
    return_url = '/en/Contact/' if request.path.startswith('/en/') else '/contact'
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    destination = request.form.get('destination', '').strip()
    travel_date = request.form.get('travel_date', '').strip()
    message = request.form.get('message', '').strip()

    if not name or not email:
        return render_template_string('''
            <!DOCTYPE html>
            <html lang="en">
            <head><meta charset="utf-8" /><title>Submission error</title></head>
            <body>
              <h1>Submission error</h1>
              <p>Please provide your name and email address.</p>
              <a href="''' + return_url + '''">Return to the contact form</a>
            </body>
            </html>
        '''), 400

    email_body = f"New inquiry submitted via Dugnic contact form:\n\n"
    email_body += f"Name: {name}\n"
    email_body += f"Email: {email}\n"
    email_body += f"Destination: {destination or 'Not specified'}\n"
    email_body += f"Preferred travel dates: {travel_date or 'Not specified'}\n\n"
    email_body += f"Message:\n{message or 'No additional message provided.'}\n"

    try:
        send_mail(f"Dugnic inquiry from {name}", email_body, reply_to=email)
    except Exception as exc:
        return render_template_string('''
            <!DOCTYPE html>
            <html lang="en">
            <head><meta charset="utf-8" /><title>Submission failed</title></head>
            <body>
              <h1>Submission failed</h1>
              <p>We could not send your inquiry right now. Please try again later.</p>
              <pre style="white-space: pre-wrap;">{{ error }}</pre>
              <a href="''' + return_url + '''">Return to the contact form</a>
            </body>
            </html>
        ''', error=str(exc)), 500

    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <title>Inquiry sent</title>
          <style>body { font-family: Arial, sans-serif; padding: 32px; background: #f8f3e7; color: #172126; } a { color: #0f5a3e; text-decoration: none; font-weight: 700; }</style>
        </head>
        <body>
          <h1>Thank you!</h1>
          <p>Your inquiry has been sent to info@dugnictravelsandexpeditions.com. We will follow up shortly.</p>
          <p><a href="''' + return_url + '''">Back to contact</a></p>
        </body>
        </html>
    ''')


@app.route('/kenya')
@app.route('/kenya/')
@app.route('/en/kenya')
@app.route('/en/kenya/')
@app.route('/en/kenya/index.html')
def kenya_page():
    return serve_static_page(os.path.join('en', 'kenya'))


@app.route('/tanzania')
@app.route('/tanzania/')
@app.route('/en/tanzania')
@app.route('/en/tanzania/')
@app.route('/en/tanzania/index.html')
def tanzania_page():
    return serve_static_page(os.path.join('en', 'tanzania'))


@app.route('/rwanda')
@app.route('/rwanda/')
@app.route('/en/rwanda')
@app.route('/en/rwanda/')
@app.route('/en/rwanda/index.html')
def rwanda_page():
    return serve_static_page(os.path.join('en', 'rwanda'))


@app.route('/zanzibar')
@app.route('/zanzibar/')
@app.route('/en/zanzibar')
@app.route('/en/zanzibar/')
@app.route('/en/zanzibar/index.html')
def zanzibar_page():
    return serve_static_page(os.path.join('en', 'zanzibar'))


@app.route('/south-africa')
@app.route('/south-africa/')
@app.route('/en/south-africa')
@app.route('/en/south-africa/')
@app.route('/en/south-africa/index.html')
def south_africa_page():
    return serve_static_page(os.path.join('en', 'south-africa'))


@app.route('/france')
@app.route('/france/')
@app.route('/en/france')
@app.route('/en/france/')
@app.route('/en/france/index.html')
def france_page():
    return serve_static_page(os.path.join('en', 'france'))


@app.route('/germany')
@app.route('/germany/')
@app.route('/en/germany')
@app.route('/en/germany/')
@app.route('/en/germany/index.html')
def germany_page():
    return serve_static_page(os.path.join('en', 'germany'))


@app.route('/thailand')
@app.route('/thailand/')
@app.route('/en/thailand')
@app.route('/en/thailand/')
@app.route('/en/thailand/index.html')
def thailand_page():
    return serve_static_page(os.path.join('en', 'thailand'))


@app.route('/london')
@app.route('/london/')
@app.route('/en/london')
@app.route('/en/london/')
@app.route('/en/london/index.html')
def london_page():
    return serve_static_page(os.path.join('en', 'london'))


@app.route('/uganda')
@app.route('/uganda/')
@app.route('/en/uganda')
@app.route('/en/uganda/')
@app.route('/en/uganda/index.html')
def uganda_page():
    return serve_static_page(os.path.join('en', 'uganda'))


@app.route('/')
def home():
    return send_from_directory(app.root_path, 'index.html')


WHATSAPP_WIDGET = '''
<a class="whatsapp-widget" href="https://wa.me/254728618281?text=Hello%20Dugnic%20Travels%2C%20I%27d%20like%20to%20plan%20a%20trip." target="_blank" rel="noopener noreferrer" aria-label="Chat with Dugnic Travels on WhatsApp">
  <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">
    <path fill="currentColor" d="M16 3a12.8 12.8 0 0 0-11 19.3L3.3 29l6.9-1.8A12.9 12.9 0 1 0 16 3Zm0 23.5c-2 0-4-.5-5.7-1.6l-.4-.2-4.1 1.1 1.1-4-.3-.4A10.5 10.5 0 1 1 16 26.5Zm5.8-7.9c-.3-.2-1.8-.9-2.1-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7.1a8.6 8.6 0 0 1-2.5-1.5 9.3 9.3 0 0 1-1.7-2.1c-.2-.3 0-.5.1-.7l.5-.5.3-.5c.1-.2 0-.4 0-.5l-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4s-1 1-1 2.3 1 2.6 1.2 2.8c.1.2 2 3.1 4.9 4.3.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2.1-1.4.3-.7.3-1.3.2-1.4s-.3-.2-.6-.4Z"/>
  </svg>
  <span>WhatsApp</span>
</a>
'''


@app.after_request
def add_whatsapp_widget(response):
    if response.mimetype != 'text/html':
        return response

    response.direct_passthrough = False
    html = response.get_data(as_text=True)
    if '/css/dugnic-renovation.css' not in html:
        head_end = html.lower().rfind('</head>')
        if head_end >= 0:
            stylesheet = '<link rel="stylesheet" href="/css/dugnic-renovation.css" />'
            html = html[:head_end] + stylesheet + html[head_end:]

    if 'class="whatsapp-widget"' not in html:
        body_end = html.lower().rfind('</body>')
        if body_end >= 0:
            html = html[:body_end] + WHATSAPP_WIDGET + html[body_end:]

    response.set_data(html)
    return response


def create_post(
    title,
    category,
    location,
    date,
    excerpt,
    content,
    media_filename=None,
    media_type=None,
    media_items=None,
):
    conn = get_db()
    cursor = conn.execute(
        '''
        INSERT INTO posts (
            title, category, location, date, excerpt, content,
            media_filename, media_type, media_items
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            title, category, location, date, excerpt, content,
            media_filename, media_type,
            json.dumps(media_items) if media_items else None,
        ),
    )
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id


def get_posts():
    conn = get_db()
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    conn.close()
    results = []
    for row in posts:
        post = dict(row)
        if post.get('media_items'):
            try:
                post['media_items'] = json.loads(post['media_items'])
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid media gallery data for blog post {post['id']}."
                ) from exc
        elif post.get('media_filename'):
            post['media_items'] = [{
                'filename': post['media_filename'],
                'type': post.get('media_type') or 'image',
            }]
        else:
            post['media_items'] = []
        results.append(post)
    return results


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
