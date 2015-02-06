#! /usr/bin/env python

"""
Simple web service to consume OpenPaths data over HTTPS and serve the most
recent OpenPaths data point over HTTP.
"""

import bottle
import datetime
import oauth2
import requests
import simplejson as json
import threading
import time


class OpenPaths(object):
    """
    Simple class to interact with data in the OpenPaths API.
    """
    def __init__(self, access, secret):
        self.url = "https://openpaths.cc/api/1"
        self.access = access
        self.secret = secret

        # Set up authentication
        self.auth_age = 0
        self.auth = self._api_auth_header()

        # Fetch most recent data point from OpenPaths
        self.last_point = None
        self.fetch_last_point()

        # Update 'self.last_point' in a loop
        self.refresh_timer = 180
        loop = threading.Thread(target=self._update_last_point)
        loop.daemon = True  # Exit when only daemon threads are left
        loop.start()

    def _api_auth_header(self):
        """
        Build an authentication header to access the OpenPaths API.

        @returns A dictionary containing authorisation header information.
        """
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

    def _update_last_point(self):
        """
        Update 'self.last_point' and run a timer when complete.
        """
        while True:
            self.last_point = self.get({"num_points": 1})
            time.sleep(self.refresh_timer)

    def fetch_last_point(self):
        """
        Update 'self.last_point' with the most recent point from OpenPaths.
        """
        self.last_point = self.get({"num_points": 1})

    def get(self, params):
        """
        Send a GET request to the OpenPaths API with the provided parameters
        as arguments in the URL.

        @param params Parameters to send in the request to the API.
        @returns A dictionary containing the JSON-ified response.
        """
        # Get the request
        response = requests.get(self.url, params=params, headers=self.auth)
        while response.status_code != 200:
            # Fetch new auth code
            self.auth = self._api_auth_header()

            # Try again
            return self.get(params)
        return json.loads(response.text)


class WhereAmI(object):
    """
    Main web app, serving out the most recent location data.
    """
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
        with open(settings_path, "r") as settings_file:
            settings = json.load(settings_file)

        return settings

    def routes(self):
        """
        Build the main routing URLs for the web app.
        """
        self.app.route("/", method="GET", callback=self.root)
        self.app.route("/lat", method="GET", callback=self.latitude)
        self.app.route("/lon", method="GET", callback=self.longitude)
        self.app.route("/time", method="GET", callback=self.time)

    def run(self, **kwargs):
        """
        Run the main Bottle instance.
        """
        self.app.run(host=self.host, port=self.port, **kwargs)

    def latitude(self):
        """
        Return the most recent OpenPaths latitude.

        @returns The most recent OpenPaths latitude as a string.
        """
        return str(self.openpaths.last_point[0]["lat"])

    def longitude(self):
        """
        Return the most recent OpenPaths longitude.

        @returns The most recent OpenPaths longitude as a string.
        """
        return str(self.openpaths.last_point[0]["lon"])

    def time(self):
        """
        Return the most recent OpenPaths update timestamp

        @returns The most recent OpenPaths timestamp.
        """
        dt = datetime.datetime.fromtimestamp(self.openpaths.last_point[0]["t"])
        return dt.isoformat()

    def root(self):
        """
        Return a message for the main web endpoint.

        @returns A message for the main app route.
        """
        return "There is nothing here. Sorry and all that."


if __name__ == "__main__":
    W = WhereAmI(host="localhost", port=6789)
    W.run(quiet=True)
