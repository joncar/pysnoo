# -*- coding: utf-8 -*-
"""TestClass for the OAuth2 Session

This ideally moves into a separate library. (along with the base class).
"""
import json

from aiohttp import BasicAuth
from asynctest import TestCase, patch, CoroutineMock, MagicMock, call
from callee import Contains

from pysnoo.oauth.oauth2_session import OAuth2Session

from tests.helpers import load_fixture

TEST_CLIENT_ID = 'oauth2_client_id'
TEST_API_URI = 'https://localhost:8080'
LOGIN_ENDPOINT = TEST_API_URI + '/login'
TOKEN_REFRESH_ENDPOINT = TEST_API_URI + 'refresh'


class TestOAuth2hSession(TestCase):
    """OAuth2 Session Test class"""

    @patch('aiohttp.client.ClientSession._request')
    async def test_fetch_token_username(self, mocked_request):
        """Test the successful fetch of an initial token by username"""
        # Setup
        token_response = load_fixture('', 'access_token_response.json')
        mocked_request.return_value.text = CoroutineMock(side_effect=[token_response])
        async with OAuth2Session(client_id=TEST_CLIENT_ID, auto_refresh_url=TOKEN_REFRESH_ENDPOINT) as oauth_session:

            self.assertFalse(oauth_session.authorized)
            self.assertEqual(oauth_session.token, {})
            self.assertIsNone(oauth_session.access_token)

            # Test
            resp = await oauth_session.fetch_token(LOGIN_ENDPOINT, code='CODE', username='USER', password='PASSWORD')

            # Check
            mocked_request.assert_called_once_with(
                'POST', LOGIN_ENDPOINT,
                data={'grant_type': 'authorization_code', 'client_id': TEST_CLIENT_ID,
                      'code': 'CODE', 'username': 'USER', 'password': 'PASSWORD'},
                timeout=None,
                headers={'Accept': 'application/json',
                         'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
                auth=BasicAuth(login='USER', password='PASSWORD', encoding='latin1'),
                verify_ssl=True)

            token_json = json.loads(token_response)
            # Library changes space-delimited array to list
            token_json['scope'] = token_json['scope'].split(' ')
            self.assertTrue(token_json.items() <= resp.items(), 'Response does not contain all Keys from Mock Payload.')
            self.assertIn('expires_at', resp)
            self.assertTrue(oauth_session.authorized)
            self.assertEqual(oauth_session.token, resp)
            self.assertEqual(oauth_session.access_token, resp['access_token'])

    @patch('aiohttp.client.ClientSession._request')
    async def test_fetch_token_client_id(self, mocked_request):
        """Test the successful fetch of an initial token by client_id"""
        # Setup
        token_response = load_fixture('', 'access_token_response.json')
        mocked_request.return_value.text = CoroutineMock(side_effect=[token_response])
        async with OAuth2Session(client_id=TEST_CLIENT_ID, auto_refresh_url=TOKEN_REFRESH_ENDPOINT) as oauth_session:

            # Test
            resp = await oauth_session.fetch_token(LOGIN_ENDPOINT, code='CODE', client_id=TEST_CLIENT_ID)

            # Check
            mocked_request.assert_called_once_with(
                'POST', LOGIN_ENDPOINT,
                data={'grant_type': 'authorization_code', 'client_id': TEST_CLIENT_ID, 'code': 'CODE'},
                timeout=None,
                headers={'Accept': 'application/json',
                         'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
                auth=BasicAuth(login=TEST_CLIENT_ID, password='', encoding='latin1'),
                verify_ssl=True)

            token_json = json.loads(token_response)
            # Library changes space-delimited array to list
            token_json['scope'] = token_json['scope'].split(' ')
            self.assertTrue(token_json.items() <= resp.items(), 'Response does not contain all Keys from Mock Payload.')
            self.assertIn('expires_at', resp)

    @patch('aiohttp.client.ClientSession._request')
    async def test_fetch_token_client_id_get(self, mocked_request):
        """Test the successful fetch of an initial token by client_id with get-method"""
        # Setup
        token_response = load_fixture('', 'access_token_response.json')
        mocked_request.return_value.text = CoroutineMock(side_effect=[token_response])
        async with OAuth2Session(client_id=TEST_CLIENT_ID, auto_refresh_url=TOKEN_REFRESH_ENDPOINT) as oauth_session:

            # Test
            resp = await oauth_session.fetch_token(LOGIN_ENDPOINT, code='CODE', client_id=TEST_CLIENT_ID, method='GET')

            # Check
            mocked_request.assert_called_once_with(
                'GET', LOGIN_ENDPOINT,
                params={'grant_type': 'authorization_code', 'client_id': TEST_CLIENT_ID, 'code': 'CODE'},
                data=None,
                timeout=None,
                allow_redirects=True,
                headers={'Accept': 'application/json',
                         'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
                auth=BasicAuth(login=TEST_CLIENT_ID, password='', encoding='latin1'),
                verify_ssl=True)

            token_json = json.loads(token_response)
            # Library changes space-delimited array to list
            token_json['scope'] = token_json['scope'].split(' ')
            self.assertTrue(token_json.items() <= resp.items(), 'Response does not contain all Keys from Mock Payload.')
            self.assertIn('expires_at', resp)

    async def test_fetch_token_fails_on_unsupported_method(self):
        """Test the failing fetch with unsupported method"""
        async with OAuth2Session(client_id=TEST_CLIENT_ID, auto_refresh_url=TOKEN_REFRESH_ENDPOINT) as oauth_session:
            with self.assertRaises(ValueError):
                await oauth_session.fetch_token(LOGIN_ENDPOINT, code='CODE', client_id=TEST_CLIENT_ID, method='HEAD')

            self.assertFalse(oauth_session.authorized)

    async def test_session_setters(self):
        """Test the successful fetch of an initial token by username"""
        # Setup
        token = json.loads(load_fixture('', 'access_token_response.json'))
        async with OAuth2Session(client_id=TEST_CLIENT_ID, auto_refresh_url=TOKEN_REFRESH_ENDPOINT) as oauth_session:

            self.assertFalse(oauth_session.authorized)
            self.assertEqual(oauth_session.client_id, TEST_CLIENT_ID)
            self.assertEqual(oauth_session.token, {})
            self.assertIsNone(oauth_session.access_token)

            oauth_session.token = token
            oauth_session.client_id = 'NEW_CLIENT_ID'
            oauth_session.access_token = 'NEW_ACCESS_TOKEN'

            self.assertTrue(oauth_session.authorized)
            self.assertEqual(oauth_session.token, token)
            self.assertEqual(oauth_session.client_id, 'NEW_CLIENT_ID')
            self.assertEqual(oauth_session.access_token, 'NEW_ACCESS_TOKEN')

    @patch('aiohttp.client.ClientSession._request')
    async def test_refresh_expired_token(self, mocked_request):
        """Test the automatic refresh of an expired token"""
        token_response = load_fixture('', 'access_token_response.json')
        token_response_dict = json.loads(token_response)
        token_response_dict['expires_in'] = -10

        mocked_tocken_updater = MagicMock()

        # Token Refresh POST
        mocked_request.return_value.text = CoroutineMock(side_effect=[token_response, 'test'])

        async with OAuth2Session(client_id=TEST_CLIENT_ID, auto_refresh_url=TOKEN_REFRESH_ENDPOINT,
                                 token=token_response_dict, token_updater=mocked_tocken_updater) as oauth_session:
            async with oauth_session.get(TEST_API_URI) as resp:
                response_body = await resp.text()
                self.assertEqual('test', response_body)

        # Check that TOKEN_REFRESH_ENDPOINT was called
        mocked_request.assert_has_calls([
            call('POST', TOKEN_REFRESH_ENDPOINT,
                 data={'grant_type': 'refresh_token',
                       'refresh_token': token_response_dict['refresh_token'],
                       'allow_redirects': 'True'},
                 timeout=None,
                 headers={'Accept': 'application/json',
                          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
                 auth=None,
                 verify_ssl=True),
            call().text(),
            call().release(),
            call('GET', TEST_API_URI,
                 headers={'Authorization': 'Bearer {}'.format(token_response_dict['access_token'])},
                 data=None,
                 allow_redirects=True),
            call().text(),
            call().release()])

        # Check that token_updater function was called with new TOKEN
        mocked_tocken_updater.assert_called_once_with(Contains('access_token'))