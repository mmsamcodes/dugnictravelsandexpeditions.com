import os
import tempfile
import unittest

from app import app, init_db, create_post, get_posts


class BlogAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, 'test_blog.sqlite3')
        app.config['TESTING'] = True
        app.config['DATABASE'] = self.db_path
        app.config['UPLOAD_FOLDER'] = os.path.join(self.temp_dir.name, 'uploads')
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

    def test_homepage_renders_branded_travel_layout(self):
        client = app.test_client()
        response = client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Dugnic Travels & Expeditions', response.get_data(as_text=True))
        self.assertIn('Stories from the road', response.get_data(as_text=True))

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

        for image_path in (
            '/assets/media/zanzibar-ocean.webp',
            '/images/1024%252C662x390%252B6%252B0/12056475/LakeDuluti.jpg',
            '/images/640/12056893/louvremuseum.jpg',
        ):
            with self.subTest(image_path=image_path):
                self.assertIn(image_path, root_html)
                image_response = client.get(image_path)
                self.assertEqual(image_response.status_code, 200)
                self.assertTrue(image_response.data)

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
        uganda_image = client.get('/images/976/12057880/Bwindi2.webp')
        zanzibar_image = client.get('/images/675/12057220/Zanzibar.jpeg')
        self.assertEqual(uganda_image.status_code, 200)
        self.assertEqual(zanzibar_image.status_code, 200)
        self.assertNotEqual(uganda_image.data, zanzibar_image.data)

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

    def test_thailand_destination_uses_flag_palette(self):
        client = app.test_client()
        response = client.get('/en/thailand/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('#002868', html)
        self.assertIn('#c60c30', html)


if __name__ == '__main__':
    unittest.main()
