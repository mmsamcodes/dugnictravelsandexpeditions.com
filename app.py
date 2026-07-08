import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, abort, jsonify, redirect, render_template, render_template_string, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'dugnic-standalone-blog-secret'
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'blog.sqlite3')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
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
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.commit()
    conn.close()


init_db()


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapped


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == 'admin' and password == 'dugnic2026':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))

    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Admin Login · Dugnic Travels</title>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
          <link href="https://fonts.googleapis.com/css2?family=Gilda+Display&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet" />
          <style>
            :root { --forest: #0f5a3e; --forest-deep: #083d2b; --gold: #c7922b; --cream: #f8f3e7; --ink: #172126; --muted: #53606a; }
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
          </style>
        </head>
        <body>
          <div class="shell">
            <div class="card">
              <div class="eyebrow">Private dashboard</div>
              <h1>Welcome back, admin</h1>
              <p>Use the dashboard to publish beautiful travel stories, upload media, and keep the homepage fresh.</p>
              <form method="post">
                <input name="username" placeholder="Username" required />
                <input name="password" type="password" placeholder="Password" required />
                <button type="submit">Enter dashboard</button>
              </form>
              <p>Demo login: admin / dugnic2026</p>
              <a class="back-link" href="/">Return to the site</a>
            </div>
          </div>
        </body>
        </html>
    ''')


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
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
          <link href="https://fonts.googleapis.com/css2?family=Gilda+Display&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet" />
          <style>
            :root { --forest: #0f5a3e; --forest-deep: #083d2b; --gold: #c7922b; --cream: #f8f3e7; --ink: #172126; --muted: #53606a; --border: rgba(8,61,43,0.1); }
            * { box-sizing: border-box; }
            body { margin: 0; font-family: "Roboto", Arial, sans-serif; background: linear-gradient(135deg, var(--cream), #fffdf8); color: var(--ink); }
            .shell { max-width: 1180px; margin: 0 auto; padding: 24px; }
            .card { background: white; border: 1px solid var(--border); border-radius: 24px; padding: 24px; box-shadow: 0 20px 48px rgba(8,61,43,0.1); margin-bottom: 18px; }
            .topbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 18px; }
            h1, h2, h3 { font-family: "Gilda Display", Georgia, serif; color: var(--forest-deep); margin: 0 0 10px; }
            p { color: var(--muted); }
            form { display: grid; gap: 12px; }
            input, textarea { width: 100%; padding: 12px 14px; border-radius: 12px; border: 1px solid #d8d0c0; font: inherit; }
            textarea { min-height: 110px; resize: vertical; }
            button { border: 0; cursor: pointer; padding: 12px 16px; border-radius: 999px; font-weight: 700; background: var(--gold); color: white; }
            .secondary-link { color: var(--forest); font-weight: 700; }
            .grid { display: grid; gap: 18px; grid-template-columns: 1.1fr 0.9fr; }
            .post-item { padding: 12px 0; border-top: 1px solid rgba(8,61,43,0.08); }
            .post-item:first-child { border-top: 0; padding-top: 0; }
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
              <a class="secondary-link" href="/admin/logout">Log out</a>
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
                  <input name="media" type="file" accept="image/*,video/*" />
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
                    {% if post.media_filename %}
                      <p>Media attached: {{ post.media_filename }}</p>
                    {% endif %}
                  </div>
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

    media_filename = None
    media_type = None
    if 'media' in request.files and request.files['media'].filename:
        upload = request.files['media']
        filename = secure_filename(upload.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        upload.save(upload_path)
        media_filename = unique_name
        media_type = 'video' if upload.mimetype.startswith('video/') else 'image'

    create_post(
        title=title,
        category=category,
        location=location,
        date=date,
        excerpt=excerpt,
        content=content,
        media_filename=media_filename,
        media_type=media_type,
    )
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))


@app.route('/api/posts')
def api_posts():
    return jsonify(get_posts())


@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/css/<path:filename>')
def css_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'css'), filename)


@app.route('/js/<path:filename>')
def js_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'js'), filename)


@app.route('/en/<path:path>')
def serve_en_pages(path):
    normalized_path = os.path.normpath(path)
    if normalized_path.startswith('..') or normalized_path == '..':
        abort(404)

    full_path = os.path.join(app.root_path, 'en', normalized_path)
    if os.path.isfile(full_path):
        return send_from_directory(os.path.join(app.root_path, 'en'), normalized_path)
    if os.path.isdir(full_path):
        index_file = os.path.join(full_path, 'index.html')
        if os.path.isfile(index_file):
            return send_from_directory(full_path, 'index.html')
    abort(404)


@app.route('/<path:path>')
def serve_static(path):
    normalized_path = os.path.normpath(path)
    if normalized_path.startswith('..') or normalized_path == '..':
        abort(404)

    full_path = os.path.join(app.root_path, normalized_path)
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
    posts = get_posts()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Dugnic Travels and Expeditions</title>
      <meta name="description" content="Discover premium safari, beach, and cultural travel experiences with Dugnic Travels and Expeditions." />
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
      <link href="https://fonts.googleapis.com/css2?family=Gilda+Display&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet" />
      <style>
        :root {
          color-scheme: light;
          --forest: #0f5a3e;
          --forest-deep: #083d2b;
          --gold: #c7922b;
          --gold-soft: #f4d68f;
          --cream: #f8f3e7;
          --ink: #172126;
          --muted: #53606a;
          --border: rgba(8, 61, 43, 0.12);
          --shadow: 0 24px 70px rgba(8, 61, 43, 0.14);
          --radius-lg: 28px;
          --radius-md: 18px;
          --font-display: "Gilda Display", Georgia, serif;
          --font-body: "Roboto", "Segoe UI", Arial, sans-serif;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: var(--font-body);
          color: var(--ink);
          line-height: 1.65;
          background: radial-gradient(circle at top left, rgba(244, 214, 143, 0.32), transparent 28%), linear-gradient(135deg, var(--cream) 0%, #fdf9f0 100%);
        }
        a { color: inherit; text-decoration: none; }
        img, video { display: block; max-width: 100%; }
        .page-shell { max-width: 1200px; margin: 0 auto; padding: 24px; }
        .site-card { background: rgba(255,255,255,0.95); border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow); overflow: hidden; }
        .topbar { display: flex; justify-content: space-between; align-items: center; padding: 20px 28px; background: linear-gradient(135deg, var(--forest-deep), var(--forest)); color: #fff; }
        .brand { font-family: var(--font-display); font-size: 1.2rem; font-weight: 700; letter-spacing: 0.04em; }
        .nav-links { display: flex; flex-wrap: wrap; gap: 8px; }
        .nav-links a { color: #fff; padding: 8px 12px; border-radius: 999px; font-weight: 600; }
        .hero { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 24px; padding: 56px 28px 42px; background: linear-gradient(120deg, rgba(8, 61, 43, 0.95), rgba(15, 90, 62, 0.94)); color: #fff; }
        .eyebrow { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 12px; padding: 6px 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 999px; background: rgba(255,255,255,0.08); font-size: 0.84rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
        .hero h1, .hero h2, section h2, section h3, .card h3, .panel h3 { font-family: var(--font-display); line-height: 1.14; letter-spacing: 0.02em; }
        .hero h1 { margin: 0 0 12px; font-size: clamp(2.2rem, 4.3vw, 3.4rem); }
        .hero p { margin: 0; font-size: 1.04rem; color: rgba(255,255,255,0.88); }
        .hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 18px; }
        .btn { display: inline-flex; align-items: center; justify-content: center; padding: 11px 16px; border-radius: 999px; font-weight: 700; }
        .btn-primary { background: var(--gold); color: #fff; }
        .btn-secondary { background: var(--cream); color: var(--forest-deep); }
        .hero-panel, .panel { background: rgba(255,255,255,0.13); border: 1px solid rgba(255,255,255,0.2); border-radius: var(--radius-md); padding: 20px; }
        section { padding: 28px; }
        .section-title { margin-bottom: 12px; color: var(--forest-deep); }
        .section-intro { max-width: 720px; color: var(--muted); margin-top: 0; }
        .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
        .card { background: #fff; border: 1px solid #e9e0d0; border-radius: var(--radius-md); padding: 18px; box-shadow: 0 10px 24px rgba(8, 61, 43, 0.05); }
        .card h3 { margin-top: 0; margin-bottom: 8px; color: var(--forest-deep); }
        .pill { display: inline-block; padding: 4px 10px; background: rgba(15, 90, 62, 0.08); color: var(--forest-deep); border-radius: 999px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; }
        .blog-shell { display: grid; gap: 18px; grid-template-columns: 1.35fr 0.65fr; align-items: start; }
        .blog-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
        .blog-card { background: #fff; border: 1px solid rgba(8, 61, 43, 0.08); border-radius: 20px; overflow: hidden; box-shadow: 0 12px 28px rgba(8, 61, 43, 0.06); }
        .blog-card__media { aspect-ratio: 4 / 3; background: linear-gradient(135deg, rgba(15, 90, 62, 0.12), rgba(199, 146, 43, 0.14)); }
        .blog-card__media img, .blog-card__media video { width: 100%; height: 100%; object-fit: cover; }
        .blog-card__body { padding: 16px; }
        .blog-card__meta, .blog-card__footer { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; color: var(--muted); font-size: 0.92rem; }
        .blog-card h3 { margin: 10px 0 8px; color: var(--forest-deep); }
        .blog-card p { margin: 0; color: var(--muted); }
        .blog-card__read { color: var(--gold); font-weight: 700; }
        .blog-sidebar { display: grid; gap: 14px; }
        .blog-panel { background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(248,243,231,0.9)); }
        .blog-panel ul { padding-left: 18px; margin: 10px 0 0; }
        footer { padding: 0 28px 28px; color: var(--muted); }
        .admin-link { display: inline-block; margin-top: 6px; color: var(--forest-deep); font-weight: 700; }
        @media (max-width: 860px) { .hero, .blog-shell { grid-template-columns: 1fr; } }
        @media (max-width: 680px) { .page-shell { padding: 14px; } .topbar { padding: 16px 18px; } .hero, section { padding-left: 18px; padding-right: 18px; } }
      </style>
    </head>
    <body>
      <div class="page-shell">
        <div class="site-card">
          <header class="topbar">
            <div class="brand">Dugnic Travels & Expeditions</div>
            <nav class="nav-links" aria-label="Primary navigation">
              <a href="/">Home</a>
              <a href="/tours">Tours</a>
              <a href="/contact">Contact</a>
              <a href="/admin/login">Admin</a>
            </nav>
          </header>

          <section class="hero">
            <div>
              <div class="eyebrow">Curated journeys • Trusted local expertise</div>
              <h1>Travel beautifully through East Africa and beyond.</h1>
              <p>From private safaris and island escapes to refined cultural journeys, we design trips that balance adventure, comfort, and unforgettable memories.</p>
              <div class="hero-actions">
                <a class="btn btn-primary" href="/tours">Explore tours</a>
                <a class="btn btn-secondary" href="/contact">Plan your trip</a>
              </div>
            </div>
            <div class="hero-panel">
              <h3>Why travelers choose us</h3>
              <ul>
                <li>Fully tailored itineraries for couples, families, and groups</li>
                <li>Thoughtful planning with local knowledge and reliable support</li>
                <li>Luxury, comfort, and authentic experiences in every destination</li>
              </ul>
            </div>
          </section>

          <main>
            <section>
              <h2 class="section-title">Designed for memorable travel</h2>
              <p class="section-intro">Every trip is shaped around your pace, interests, and sense of comfort so the journey feels effortless from the first idea to the final arrival.</p>
              <div class="grid">
                <article class="card"><h3>Inspired by the wild</h3><p>Safaris, coastlines, and landscapes are arranged with care, giving each journey a sense of wonder and calm.</p></article>
                <article class="card"><h3>Built for comfort</h3><p>We blend premium stays, easy logistics, and expert guidance into a smooth and welcoming experience.</p></article>
                <article class="card"><h3>Ready when you are</h3><p>Share your preferred pace, budget, and destination and we will shape a trip around your travel style.</p></article>
              </div>
            </section>

            <section>
              <h2 class="section-title">Our services</h2>
              <p class="section-intro">Beyond curated trips, we also support clients with end-to-end travel and event solutions designed for businesses and private travelers alike.</p>
              <div class="grid">
                <article class="card"><h3>Tourism Consultancy</h3><p>Strategic guidance for destinations, travel planning, and growth-focused tourism initiatives.</p></article>
                <article class="card"><h3>Destination Marketing</h3><p>Tailored marketing support that helps destinations and experiences reach the right audiences.</p></article>
                <article class="card"><h3>Tour Services</h3><p>Seamless tour planning, logistics, and itinerary support for memorable journeys.</p></article>
                <article class="card"><h3>Travel Management</h3><p>Professional coordination for efficient, comfortable, and well-organized travel arrangements.</p></article>
                <article class="card"><h3>Training</h3><p>Capacity-building and travel industry training solutions that strengthen teams and service delivery.</p></article>
                <article class="card"><h3>Events</h3><p>Carefully organized event experiences that blend planning precision with memorable execution.</p></article>
                <article class="card"><h3>MICE</h3><p>Meetings, incentives, conferences, and exhibitions managed with professionalism and purpose.</p></article>
              </div>
            </section>

            <section class="cta-banner">
              <div class="split">
                <div>
                  <h2 class="section-title">Start with a destination</h2>
                  <p class="section-intro">Whether you are planning a safari, a beach retreat, or a cultural escape, we will turn it into a refined itinerary you will remember.</p>
                </div>
                <div class="hero-actions">
                  <a class="btn btn-primary" href="/tours">Browse destinations</a>
                  <a class="btn btn-secondary" href="/contact">Talk to an advisor</a>
                </div>
              </div>
            </section>

            <section class="blog-section" id="blog-showcase">
              <div class="section-heading">
                <div class="eyebrow">Stories from the road</div>
                <h2 class="section-title">A home for fresh trip updates and inspiration</h2>
                <p class="section-intro">Step into a collection of inspiring travel stories, destination highlights, and unforgettable journeys designed to spark your next adventure.</p>
              </div>
              <div class="blog-shell">
                <div class="blog-grid">
                  {% for post in posts %}
                    <article class="blog-card">
                      <div class="blog-card__media">
                        {% if post.media_filename %}
                          {% if post.media_type == 'video' %}
                            <video controls preload="metadata" src="/media/{{ post.media_filename }}"></video>
                          {% else %}
                            <img src="/media/{{ post.media_filename }}" alt="{{ post.title }}" />
                          {% endif %}
                        {% else %}
                          <div class="blog-card__placeholder"></div>
                        {% endif %}
                      </div>
                      <div class="blog-card__body">
                        <div class="blog-card__meta">
                          <span class="pill">{{ post.category }}</span>
                          <span>{{ post.date }}</span>
                        </div>
                        <h3>{{ post.title }}</h3>
                        <p>{{ post.excerpt }}</p>
                        <div class="blog-card__footer">
                          <span>{{ post.location }}</span>
                          <span class="blog-card__read">Read story →</span>
                        </div>
                      </div>
                    </article>
                  {% endfor %}
                </div>
                <aside class="blog-sidebar">
                  <div class="panel blog-panel">
                    <h3>For the team</h3>
                    <a class="btn btn-primary admin-link" href="/admin/login">Open admin dashboard</a>
                  </div>
                  <div class="panel blog-panel">
                    <h3>What can be shared</h3>
                    <ul>
                      <li>Trip highlights and destination notes</li>
                      <li>Photo galleries and short videos</li>
                      <li>Tour launches, itineraries, and seasonal updates</li>
                    </ul>
                  </div>
                </aside>
              </div>
            </section>
          </main>

          <footer>
            <p>Start with a destination, and we will shape the rest around your travel style.</p>
          </footer>
        </div>
      </div>
    </body>
    </html>
    ''', posts=posts)


def create_post(title, category, location, date, excerpt, content, media_filename=None, media_type=None):
    conn = get_db()
    cursor = conn.execute(
        '''
        INSERT INTO posts (title, category, location, date, excerpt, content, media_filename, media_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (title, category, location, date, excerpt, content, media_filename, media_type),
    )
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id


def get_posts():
    conn = get_db()
    posts = conn.execute(
        'SELECT * FROM posts ORDER BY id DESC'
    ).fetchall()
    conn.close()
    return [dict(post) for post in posts]


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
