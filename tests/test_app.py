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

    def test_tours_and_contact_pages_render(self):
        client = app.test_client()

        tours_response = client.get('/tours')
        self.assertEqual(tours_response.status_code, 200)
        self.assertIn('Featured destinations', tours_response.get_data(as_text=True))

        contact_response = client.get('/contact')
        self.assertEqual(contact_response.status_code, 200)
        self.assertIn('Plan your next journey', contact_response.get_data(as_text=True))

    def test_css_asset_serves_correctly(self):
        client = app.test_client()
        response = client.get('/css/dugnic-renovation.css')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/css', response.content_type)

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

    def test_thailand_destination_uses_flag_palette(self):
        client = app.test_client()
        response = client.get('/en/thailand/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('#002868', html)
        self.assertIn('#c60c30', html)


if __name__ == '__main__':
    unittest.main()
