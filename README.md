# dugnictravelsandexpeditions.com

Flask-powered travel site with a SQLite-backed blog and admin dashboard.

## Local setup

1. Install Python 3.10 or newer.
2. Install dependencies with `pip install -r requirements.txt`.
3. Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in the environment before starting the app. The admin user is created or updated from these values, and only a password hash is stored in SQLite.
4. Set a persistent `SECRET_KEY` before deploying. `SESSION_COOKIE_SECURE=true` should be enabled when the site is served over HTTPS.
5. Run `python app.py` and visit `/admin/login` to sign in.

The admin username and password are never embedded in the source files. If either environment variable is missing, the admin login fails closed.

## cPanel deployment

SQLite is sufficient for this single-admin site and its blog; a separate MySQL database server is not required. The SQLite file must live in a writable, persistent directory and must not be served publicly.

1. In cPanel, create a Python application and select Python 3.10 or newer. Set the application root to the project directory and enable its virtual environment.
2. Upload the project files to that application root. Install the dependencies from `requirements.txt` using the virtual environment's pip.
3. Create a private, writable data directory outside `public_html`, for example `/home/CPANEL_USER/dugnic-data`. Ensure the cPanel application user can write to it.
4. Add these environment variables in the cPanel Python application settings:
   - `SECRET_KEY`: a long random value generated for this deployment.
   - `ADMIN_USERNAME`: `admin`.
   - `ADMIN_PASSWORD`: the strong password chosen for the admin account. Do not put it in this repository.
   - `DATABASE_PATH`: an absolute path in the private data directory, such as `/home/CPANEL_USER/dugnic-data/blog.sqlite3`.
   - `UPLOAD_FOLDER`: an absolute path for persistent uploaded blog media, such as `/home/CPANEL_USER/dugnic-data/uploads`.
   - `SESSION_COOKIE_SECURE`: `true` after HTTPS is enabled.
5. Set the cPanel startup file to `passenger_wsgi.py`, with this content:

   ```python
   from app import app as application
   ```

   If cPanel generated a startup file already, preserve its path setup and expose the Flask object as `application`. Restart the application. On startup, the app creates/migrates its SQLite tables and initializes the admin account using the environment variables.
6. Keep the data directory in persistent storage during deployments and backups. Do not place it under a publicly served directory. Ensure the app process can create the SQLite database and upload directory.
7. Enable HTTPS, then test `/`, `/admin/login`, `/admin/dashboard`, `/api/posts`, and the contact form. The blog dashboard is protected by the server-side login; the browser does not store an admin login flag or password.

### Updating the site without losing blog content

The website code and blog data are separate only when `DATABASE_PATH` and `UPLOAD_FOLDER` point to the private persistent data directory described above. Before changing or uploading site files:

1. Confirm those two cPanel environment variables point outside the application root and `public_html`.
2. Back up the SQLite database file and the entire uploads directory.
3. Upload or replace only website code and static assets. Do not delete, overwrite, or include the private data directory in a site-file replacement.
4. Restart the app and confirm existing posts and uploaded media still appear.

If either environment variable is unset, the app defaults to `blog.sqlite3` and `uploads` inside the application directory. In that configuration, replacing or deleting the application directory can affect blog content and media. Back up and configure the existing production data paths before doing a code-only update; do not point the app at a new empty database unless you intend to start a separate blog.

To rotate the admin password, update `ADMIN_PASSWORD` in cPanel and restart the app. The configured credentials are re-hashed into the database at startup.
