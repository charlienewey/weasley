#! /usr/bin/env python

import bottle
import oauth2
import requests
import simplejson as json
import time


class OpenPaths(object):
    def __init__(self, access, secret, header_max_age=50):
        self.url = "https://openpaths.cc/api/1"
        self.access = access
        self.secret = secret

        self.header_age = 0
        self.header_max_age = header_max_age
        self.header = self._api_auth_header()

    def _api_auth_header(self):
        consumer = oauth2.Consumer(key=self.access, secret=self.secret)
        params = {
            "oauth_consumer_key": consumer.key,
            "oauth_nonce": oauth2.generate_nonce(),
            "oauth_timestamp": int(time.time()),
            "oauth_version": "1.0"
        }

        request = oauth2.Request(method="GET", url=self.url, parameters=params)
        request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, None)

        return request.to_header()

    def get(self, params):
        # If header age > max age, then fetch a new one
        self.header_age += 1
        if self.header_age > self.header_max_age:
            self.header = self._api_auth_header()

        # Get the request
        response = requests.get(self.url, params=params,
                                headers=self.header).text

        return json.loads(response)

    def get_last_coordinate(self):
        return self.get({"num_points": 1})


class Weasel(object):
    def __init__(self, host, port, settings_path="settings.json"):
        # Set instance variables
        self.host = host
        self.port = port

        # Initialise app and route
        self.app = bottle.Bottle()
        self.routes()

        # Load settings
        self.settings = self.load_settings(settings_path)
        self.openpaths = OpenPaths(self.settings["keys"]["access"],
                                   self.settings["keys"]["secret"])

    def load_settings(self, settings_path):
        """
        Read the application settings.

        @param settings_path Path to JSON file containing application settings.
        @returns A dictionary containing the application settings.
        """
        with open(settings_path, "r") as s:
            settings = json.load(s)

        return settings

    def routes(self):
        self.app.route("/lat", method="GET", callback=self.latitude)

    def run(self):
        self.app.run(host=self.host, port=self.port)

    def latitude(self):
        return "Hi :)"


if __name__ == "__main__":
    w = Weasel(host="localhost", port=6789)
    w.run()
