from django.test import TestCase
from django.urls import reverse
from search.models import Anime

class SuggestionsViewTest(TestCase):
    def setUp(self):
        Anime.objects.create(name='Naruto')
        Anime.objects.create(name='Death Note')

    def test_no_query(self):
        response = self.client.get(reverse('suggestions'))
        self.assertJSONEqual(response.content, [])

    def test_found_suggestions(self):
        response = self.client.get(reverse('suggestions'), {'q': 'nar'})
        self.assertContains(response, 'Naruto')


class ClearViewTest(TestCase):
    def test_clears_chat_history(self):
        session = self.client.session
        session['chat_messages'] = [{'role': 'user', 'content': 'test'}]
        session.save()
        response = self.client.get(reverse('clear'))
        self.assertNotIn('chat_messages', self.client.session)
        self.assertEqual(response.status_code, 302)


class SearchViewTest(TestCase):
    databases = {'default', 'media'}
    def setUp(self):
        self.anime = Anime.objects.create(name='One Piece')

    def test_search_found(self):
        response = self.client.get(reverse('search'), {'q': 'One'})
        self.assertContains(response, 'One Piece')

    def test_search_not_found(self):
        response = self.client.get(reverse('search'), {'q': 'NotExist'})
        self.assertContains(response, 'messages')

    def test_ajax_request(self):
        self.client.get(reverse('search'), {'q': 'One'})
        response = self.client.get(
            reverse('search'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('messages', response.json())


from unittest.mock import patch, MagicMock
class MediaProxyViewTest(TestCase):
    @patch('search.views.requests.get')
    def test_media_proxy_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Content-Type': 'video/mp4'}
        mock_resp.iter_content = lambda chunk_size: [b'data']
        mock_get.return_value = mock_resp

        response = self.client.get('/media-proxy/somefile.mp4')
        self.assertEqual(response.status_code, 200)
