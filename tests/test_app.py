from io import BytesIO
import os
import sqlite3
import tempfile
import unittest
from hashlib import sha256
from html.parser import HTMLParser

from app import app, init_db, create_post, get_posts


class GalleryMediaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_gallery = False
        self.gallery_depth = 0
        self.images = []
        self.videos = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()
        if not self.in_gallery and tag == 'div' and 'media-grid' in classes:
            self.in_gallery = True
            self.gallery_depth = 1
            return

        if not self.in_gallery:
            return

        if tag == 'div':
            self.gallery_depth += 1
        elif tag == 'img':
            self.images.append(attributes.get('src'))
        elif tag in ('video', 'iframe'):
            self.videos.append(attributes.get('src'))

    def handle_endtag(self, tag):
        if self.in_gallery and tag == 'div':
            self.gallery_depth -= 1
            if self.gallery_depth == 0:
                self.in_gallery = False


class BlogAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, 'test_blog.sqlite3')
        app.config['TESTING'] = True
        app.config['DATABASE'] = self.db_path
        app.config['UPLOAD_FOLDER'] = os.path.join(self.temp_dir.name, 'uploads')
        app.config['ADMIN_USERNAME'] = 'test-admin'
        app.config['ADMIN_PASSWORD'] = 'test-only-password'
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        with app.app_context():
            init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_list_post(self):
        with app.app_context():
            post_id = create_post(
                title='Test safari story',
                category='Safari',
                location='Ruaha',
                date='2026-07-08',
                excerpt='A short intro',
                content='Full story body',
                media_filename='sample.jpg',
                media_type='image',
            )
            posts = get_posts()

        self.assertEqual(post_id, 1)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['title'], 'Test safari story')
        self.assertEqual(posts[0]['category'], 'Safari')
        self.assertEqual(posts[0]['media_items'], [{
            'filename': 'sample.jpg',
            'type': 'image',
        }])

    def test_existing_posts_database_gets_gallery_column(self):
        legacy_db_path = os.path.join(self.temp_dir.name, 'legacy_blog.sqlite3')
        conn = sqlite3.connect(legacy_db_path)
        conn.execute('''
            CREATE TABLE posts (
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
        ''')
        conn.execute(
            'INSERT INTO posts (title, category, content, media_filename, media_type) VALUES (?, ?, ?, ?, ?)',
            ('Older story', 'Safari', 'Story content', 'older.jpg', 'image'),
        )
        conn.commit()
        conn.close()

        original_db_path = app.config['DATABASE']
        app.config['DATABASE'] = legacy_db_path
        try:
            with app.app_context():
                init_db()
                post = get_posts()[0]
                conn = sqlite3.connect(legacy_db_path)
                columns = {row[1] for row in conn.execute('PRAGMA table_info(posts)')}
                conn.close()
            self.assertIn('media_items', columns)
            self.assertEqual(post['media_items'], [{
                'filename': 'older.jpg',
                'type': 'image',
            }])
        finally:
            app.config['DATABASE'] = original_db_path

    def test_admin_can_publish_multiple_images_and_videos_in_gallery(self):
        client = app.test_client()
        login_response = client.post('/admin/login', data={
            'username': 'test-admin',
            'password': app.config['ADMIN_PASSWORD'],
        })
        self.assertEqual(login_response.status_code, 302)

        dashboard_html = client.get('/admin/dashboard').get_data(as_text=True)
        self.assertIn('name="media"', dashboard_html)
        self.assertIn('type="file" accept="image/*,video/*" multiple', dashboard_html)
        self.assertIn('Select one or more photos and videos.', dashboard_html)

        response = client.post('/admin/posts', data={
            'title': 'Safari gallery',
            'category': 'Safari',
            'location': 'Ruaha',
            'date': '2026-07-08',
            'excerpt': 'A gallery of the journey',
            'content': 'Story content',
            'media': [
                (BytesIO(b'image-data'), 'safari.jpg', 'image/jpeg'),
                (BytesIO(b'video-data'), 'drive.mp4', 'video/mp4'),
                (BytesIO(b'another-image'), 'landscape.png', 'image/png'),
            ],
        }, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 302)

        posts = client.get('/api/posts').get_json()
        self.assertEqual(len(posts), 1)
        self.assertEqual(
            [item['type'] for item in posts[0]['media_items']],
            ['image', 'video', 'image'],
        )
        self.assertEqual(posts[0]['media_filename'], posts[0]['media_items'][0]['filename'])
        for item in posts[0]['media_items']:
            with self.subTest(filename=item['filename']):
                media_response = client.get(f"/media/{item['filename']}")
                self.assertEqual(media_response.status_code, 200)
                self.assertTrue(media_response.data)

    def test_admin_can_delete_post_and_its_media(self):
        media_filename = 'test-upload.jpg'
        video_filename = 'test-upload.mp4'
        media_path = os.path.join(app.config['UPLOAD_FOLDER'], media_filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        with open(media_path, 'wb') as media_file:
            media_file.write(b'test media')
        with open(video_path, 'wb') as video_file:
            video_file.write(b'test video')

        with app.app_context():
            post_id = create_post(
                title='Story to delete',
                category='Safari',
                location='Ruaha',
                date='2026-07-08',
                excerpt='A short intro',
                content='Full story body',
                media_filename=media_filename,
                media_type='image',
                media_items=[
                    {'filename': media_filename, 'type': 'image'},
                    {'filename': video_filename, 'type': 'video'},
                ],
            )
            other_post_id = create_post(
                title='Story to keep',
                category='Culture',
                location='Zanzibar',
                date='2026-07-09',
                excerpt='Another intro',
                content='Another story body',
            )

        client = app.test_client()
        unauthorized_response = client.post(f'/admin/posts/{post_id}/delete')
        self.assertEqual(unauthorized_response.status_code, 302)
        self.assertTrue(os.path.exists(media_path))
        self.assertTrue(os.path.exists(video_path))

        login_response = client.post('/admin/login', data={
            'username': 'test-admin',
            'password': app.config['ADMIN_PASSWORD'],
        })
        self.assertEqual(login_response.status_code, 302)

        dashboard_response = client.get('/admin/dashboard')
        dashboard_html = dashboard_response.get_data(as_text=True)
        self.assertIn('.shell .card p { color: #37444b;', dashboard_html)
        self.assertIn('input::placeholder, textarea::placeholder { color: #59636b;', dashboard_html)
        self.assertIn(f'/admin/posts/{post_id}/delete', dashboard_html)
        self.assertIn('Delete story', dashboard_html)

        delete_response = client.post(f'/admin/posts/{post_id}/delete')
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(os.path.exists(media_path))
        self.assertFalse(os.path.exists(video_path))
        with app.app_context():
            remaining_posts = get_posts()
        self.assertEqual([post['id'] for post in remaining_posts], [other_post_id])

        missing_response = client.post(f'/admin/posts/{post_id}/delete')
        self.assertEqual(missing_response.status_code, 404)

    def test_homepage_renders_branded_travel_layout(self):
        client = app.test_client()
        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Dugnic Travels & Expeditions', response.get_data(as_text=True))
        self.assertIn('Stories from the road', response.get_data(as_text=True))

    def test_whatsapp_widget_links_to_business_number_on_home_and_contact(self):
        client = app.test_client()
        expected_link = 'https://wa.me/254728618281?text=Hello%20Dugnic%20Travels%2C%20I%27d%20like%20to%20plan%20a%20trip.'

        for route in ('/', '/en/Contact/'):
            with self.subTest(route=route):
                response = client.get(route)
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('class="whatsapp-widget"', html)
                self.assertIn(expected_link, html)
                self.assertIn('aria-label="Chat with Dugnic Travels on WhatsApp"', html)

    def test_whatsapp_widget_is_injected_once_on_site_and_admin_pages(self):
        client = app.test_client()
        for route in ('/', '/en/kenya/', '/en/tours/', '/admin/login'):
            with self.subTest(route=route):
                response = client.get(route)
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(html.count('class="whatsapp-widget"'), 1)
                self.assertIn('/css/dugnic-renovation.css', html)

    def test_admin_login_uses_hashed_database_credentials_and_protects_dashboard(self):
        client = app.test_client()
        unauthorized = client.get('/admin/dashboard')
        self.assertEqual(unauthorized.status_code, 302)
        self.assertIn('/admin/login', unauthorized.headers['Location'])

        bad_login = client.post('/admin/login', data={
            'username': 'test-admin',
            'password': 'wrong-password',
        })
        self.assertEqual(bad_login.status_code, 200)
        self.assertIn('Invalid username or password.', bad_login.get_data(as_text=True))
        self.assertEqual(client.get('/admin/dashboard').status_code, 302)

        with app.app_context():
            conn = sqlite3.connect(app.config['DATABASE'])
            row = conn.execute(
                'SELECT password_hash FROM admin_users WHERE username = ?',
                ('test-admin',),
            ).fetchone()
            conn.close()
        self.assertIsNotNone(row)
        self.assertNotEqual(row[0], app.config['ADMIN_PASSWORD'])
        self.assertTrue(row[0].startswith('scrypt:'))

        login_response = client.post('/admin/login', data={
            'username': 'test-admin',
            'password': app.config['ADMIN_PASSWORD'],
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertIn('/admin/dashboard', login_response.headers['Location'])
        self.assertEqual(client.get('/admin/dashboard').status_code, 200)

        logout_response = client.post('/admin/logout')
        self.assertEqual(logout_response.status_code, 302)
        self.assertEqual(client.get('/admin/dashboard').status_code, 302)

    def test_blog_frontend_has_no_demo_login_credentials_or_local_auth(self):
        client = app.test_client()
        response = client.get('/js/blog.js')
        source = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('dugnic2026', source)
        self.assertNotIn('dugnicBlogAuth', source)
        self.assertIn("fetch('/api/posts')", source)

    def test_homepage_routes_share_video_dropdown_and_video_assets(self):
        client = app.test_client()
        root_response = client.get('/')
        en_response = client.get('/en/')
        root_html = root_response.get_data(as_text=True)

        self.assertEqual(root_response.status_code, 200)
        self.assertEqual(en_response.status_code, 200)
        self.assertEqual(root_response.data, en_response.data)
        self.assertIn('Pick a niche:', root_html)
        self.assertIn('Adventure Tourism', root_html)
        self.assertIn('Luxury Experiences', root_html)
        self.assertEqual(root_html.count("media:{type:'video'"), 2)
        self.assertEqual(root_html.count("media:{type:'image'"), 6)
        self.assertNotIn('youtube-nocookie.com/embed', root_html)
        self.assertNotIn("provider:'youtube'", root_html)
        niche_image_paths = (
            '/images/1200/11928382/LakeNaivasha6.jpeg',
            '/images/1024/11928458/silver-palm-spa-resort1.webp',
            '/images/675/12372266/johan4.jpg',
            '/assets/media/uganda-wildlife-trail.webp',
            '/assets/media/zanzibar-coast-drive.jpg',
            '/images/1920/12058258/sands-at-chale-island-4.webp',
        )
        for image_path in niche_image_paths:
            with self.subTest(niche_image_path=image_path):
                self.assertIn(image_path, root_html)
                self.assertEqual(client.get(image_path).status_code, 200)
        self.assertIn("img.src = media.src;", root_html)
        self.assertIn("play.hidden = true;", root_html)
        self.assertNotIn("createElement('iframe')", root_html)
        self.assertEqual(root_html.count('<article class="media-slide">'), 10)
        self.assertIn('const autoplayInterval = 5000;', root_html)

        home_image_hashes = []
        for image_path in (
            '/images/1920/11928473/Amboseli1.jpg',
            '/assets/media/tanzania-safari-poster.jpg',
            '/images/675/12057321/Nyungwe3.jpeg',
            '/images/976/12057880/Bwindi2.webp',
            '/images/675/12057220/Zanzibar.jpeg',
            '/images/675/12372340/johan3.jpg',
            '/images/640/12056885/Versailles.jpg',
            '/images/540/12057064/RhineValley.jpeg',
            '/assets/media/destinations/thailand-limestone-lagoon.webp',
            '/assets/media/destinations/commons-london-home.webp',
        ):
            with self.subTest(image_path=image_path):
                self.assertIn(image_path, root_html)
                image_response = client.get(image_path)
                self.assertEqual(image_response.status_code, 200)
                self.assertTrue(image_response.data)
                home_image_hashes.append(sha256(image_response.data).hexdigest())
        self.assertEqual(len(home_image_hashes), 10)
        self.assertEqual(len(set(home_image_hashes)), 10)

        home_carousel_images = [
            slide.split('<img ', 1)[1].split('src="', 1)[1].split('"', 1)[0]
            for slide in root_html.split('<article class="media-slide">')[1:11]
        ]
        self.assertEqual(len(home_carousel_images), 10)
        self.assertEqual(len(set(home_carousel_images)), 10)

        for video_path in (
            '/assets/media/rwanda-gorilla-trek-web.mp4',
            '/assets/media/tanzania-drive-safari-web.mp4',
        ):
            with self.subTest(video_path=video_path):
                video_response = client.get(video_path, headers={'Range': 'bytes=0-1'})
                self.assertIn(video_response.status_code, (200, 206))
                self.assertTrue(video_response.content_type.startswith('video/mp4'))

    def test_tours_and_contact_pages_render(self):
        client = app.test_client()

        tours_response = client.get('/tours')
        self.assertEqual(tours_response.status_code, 200)
        self.assertIn('Featured destinations', tours_response.get_data(as_text=True))
        tours_html = tours_response.get_data(as_text=True)
        self.assertIn('/images/976/12057880/Bwindi2.webp', tours_html)
        self.assertIn('/images/675/12057220/Zanzibar.jpeg', tours_html)
        self.assertIn('/images/1024%252C662x390%252B6%252B0/12056475/LakeDuluti.jpg', tours_html)
        self.assertIn('class="grid destination-grid"', tours_html)
        self.assertIn('/assets/media/destinations/commons-london-tours.webp', tours_html)
        self.assertIn('London from Primrose Hill, May 2013', tours_html)
        uganda_image = client.get('/images/976/12057880/Bwindi2.webp')
        zanzibar_image = client.get('/images/675/12057220/Zanzibar.jpeg')
        tanzania_image = client.get('/images/1024%252C662x390%252B6%252B0/12056475/LakeDuluti.jpg')
        london_image = client.get('/assets/media/destinations/commons-london-tours.webp')
        self.assertEqual(uganda_image.status_code, 200)
        self.assertEqual(zanzibar_image.status_code, 200)
        self.assertEqual(tanzania_image.status_code, 200)
        self.assertEqual(london_image.status_code, 200)
        self.assertEqual(len({uganda_image.data, zanzibar_image.data, tanzania_image.data, london_image.data}), 4)

        contact_response = client.get('/contact')
        self.assertEqual(contact_response.status_code, 200)
        self.assertIn('Plan your next journey', contact_response.get_data(as_text=True))

    def test_logo_asset_serves_correctly(self):
        client = app.test_client()
        response = client.get('/downloads/logo.jpeg')

        self.assertEqual(response.status_code, 200)
        self.assertIn('image/jpeg', response.content_type)

    def test_css_asset_serves_correctly(self):
        client = app.test_client()
        response = client.get('/css/dugnic-renovation.css')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/css', response.content_type)

    def test_js_asset_serves_correctly(self):
        client = app.test_client()
        response = client.get('/js/blog.js')

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/javascript', response.content_type)

    def test_homepage_restores_conversion_sections(self):
        client = app.test_client()
        response = client.get('/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Start with a destination', html)
        self.assertIn('Explore tours', html)
        self.assertIn('Plan your trip', html)

    def test_destination_pages_remain_accessible(self):
        client = app.test_client()
        response = client.get('/en/kenya/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Kenya, the birthplace of the safari', html)

    def test_destination_galleries_use_destination_specific_media(self):
        client = app.test_client()
        expected_media = {
            'france': '/assets/media/destinations/paris-eiffel-tower.webp',
            'germany': '/assets/media/destinations/germany-heidelberg-bridge.webp',
            'kenya': '/assets/media/kenya-elephant.webp',
            'london': '/assets/media/destinations/london-buckingham-palace.webp',
            'rwanda': '/assets/media/rwanda-gorilla-trek-web.mp4',
            'south-africa': '/assets/media/destinations/south-africa-cape-town.webp',
            'tanzania': '/assets/media/tanzania-drive-safari-web.mp4',
            'thailand': '/assets/media/destinations/bangkok-grand-palace.webp',
            'uganda': '/assets/media/destinations/uganda-kibale-chimpanzee.webp',
            'zanzibar': '/assets/media/zanzibar-aerial-coastline-web.mp4',
        }

        for destination, media_path in expected_media.items():
            with self.subTest(destination=destination):
                page_response = client.get(f'/en/{destination}/')
                html = page_response.get_data(as_text=True)
                self.assertEqual(page_response.status_code, 200)
                self.assertIn(media_path, html)
                self.assertNotIn('interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4', html)
                media_response = client.get(media_path)
                self.assertEqual(media_response.status_code, 200)
                self.assertTrue(media_response.data)

    def test_destination_carousels_have_ten_unique_photos_and_one_unique_video(self):
        client = app.test_client()
        image_sources = []
        image_hashes = []
        video_sources = []

        for destination in (
            'france', 'germany', 'kenya', 'london', 'rwanda',
            'south-africa', 'tanzania', 'thailand', 'uganda', 'zanzibar',
        ):
            with self.subTest(destination=destination):
                response = client.get(f'/en/{destination}/')
                self.assertEqual(response.status_code, 200)
                gallery = GalleryMediaParser()
                gallery.feed(response.get_data(as_text=True))
                self.assertEqual(len(gallery.images), 10)
                self.assertEqual(len(set(gallery.images)), 10)
                self.assertEqual(len(gallery.videos), 1)
                self.assertIn('Wikimedia Commons', response.get_data(as_text=True))
                for image_source in gallery.images:
                    image_response = client.get(image_source)
                    self.assertEqual(image_response.status_code, 200, image_source)
                    image_hashes.append(sha256(image_response.get_data()).hexdigest())
                image_sources.extend(gallery.images)
                video_sources.extend(gallery.videos)

        self.assertEqual(len(set(image_sources)), 100)
        self.assertEqual(len(set(image_hashes)), 100)
        self.assertEqual(len(set(video_sources)), 10)

    def test_short_destination_galleries_use_distinct_local_photos(self):
        client = app.test_client()
        gallery_photos = {
            'france': ('/images/640/12056893/louvremuseum.jpg',),
            'germany': ('/images/675/12057051/Cathedral2.jpeg',),
            'kenya': (
                '/images/1024%252C1223x720%252B28%252B0/12078166/L.Nakuru1.jpg',
                '/images/1024%252C662x390%252B6%252B0/12058369/Kilifi1.jpeg',
            ),
            'tanzania': ('/images/675/12057844/Sere4.jpeg',),
        }

        for destination, image_paths in gallery_photos.items():
            with self.subTest(destination=destination):
                page_response = client.get(f'/en/{destination}/')
                html = page_response.get_data(as_text=True)
                self.assertEqual(page_response.status_code, 200)
                self.assertEqual(len(set(image_paths)), len(image_paths))

                for image_path in image_paths:
                    with self.subTest(image_path=image_path):
                        self.assertIn(image_path, html)
                        image_response = client.get(image_path)
                        self.assertEqual(image_response.status_code, 200)
                        self.assertTrue(image_response.data)

    def test_thailand_gallery_omits_duplicate_grand_palace_photo_variant(self):
        client = app.test_client()
        response = client.get('/en/thailand/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('/assets/media/destinations/bangkok-grand-palace.webp', html)
        self.assertNotIn('/images/675/12057115/Grandpalace.jpg', html)

    def test_thailand_destination_uses_flag_palette(self):
        client = app.test_client()
        response = client.get('/en/thailand/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('#002868', html)
        self.assertIn('#c60c30', html)


if __name__ == '__main__':
    unittest.main()
