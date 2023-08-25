import re
from requests_oauthlib import OAuth1Session
import tweepy


class Tweet:
    def __init__(self, api_key, api_key_secret, access_token, access_token_secret):
        self.api_key = api_key
        self.api_key_secret = api_key_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.post_url = 'https://api.twitter.com/2/tweets'
        twitter_auth = tweepy.OAuth1UserHandler(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )
        self.twitter = tweepy.API(twitter_auth)
        self.oauth = OAuth1Session(None)
        self.authenticated = False
        self.__authenticate()

    def __authenticate(self):
        if not self.authenticated:
            try:
                self.twitter.verify_credentials()
                self.authenticated = True
                self.oauth = OAuth1Session(
                    self.api_key,
                    self.api_key_secret,
                    self.access_token,
                    self.access_token_secret
                )
            except Exception as e:
                print('Invalid tokens supplied for Twitter:', e)
                self.twitter.session.close()

    def close(self):
        self.twitter.session.close()

    def post(self, text, image_name=None):
        if self.authenticated:
            if text is None and image_name is None:
                print('Must either provide a caption or a picture to post on Twitter.')
            else:
                payload = {}
                if text is not None:
                    payload['text'] = text
                if image_name is not None:
                    post = self.twitter.simple_upload(image_name)
                    text = str(post)
                    media_id = re.search("media_id=(.+?),", text).group(1)
                    media_json = {"media_ids": ['{}'.format(media_id)]}
                    payload['media'] = media_json
                resp = self.oauth.post(self.post_url, json=payload)
                if resp.status_code < 200 or resp.status_code > 299:
                    print(resp.json())
                    print('Failed to post to Twitter.')
                    return -1
