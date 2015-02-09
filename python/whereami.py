#! /usr/bin/env python

"""
"""

import math
import oauth2
import requests
import simplejson as json
import time


class Location(object):
    """
    Simple class for (lat, lon) pairs.
    """
    def __init__(self, name, lat, lon, radius=6371000):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.radius = radius

    def is_near(self, loc, dist):
        """
        Returns True if "loc" is within "dist" distance of self.
        """
        if self.distance(loc) <= dist:
            return True
        return False

    def distance(self, loc):
        """
        Returns the Great Circle distance between "self" and "loc".
        """
        slon = math.radians(self.lon - loc.lon)
        slat = math.radians(self.lat)
        lat = math.radians(loc.lat)

        dx = math.pow(math.cos(slon) * math.cos(slat) - math.cos(lat), 2)
        dy = math.pow(math.sin(slon) * math.cos(slat), 2)
        dz = math.pow(math.sin(slat) - math.sin(lat), 2)

        return math.asin(math.sqrt(dx + dy + dz) / 2) * (2 * self.radius)


class OpenPathsAPI(object):
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

    def get_last_location(self):
        last_loc = self.get({"num_points": 1})
        return Location("last_location", last_loc["lat"], last_loc["lon"])


class SparkAPI(object):
    def __init__(self, username, password, device):
        self.url = "https://api.spark.io"

        self.username = username
        self.password = password
        self.device = device

        self.token = None
        self.expiry = None
        self._new_token()

    def _new_token(self):
        headers = {"encoding": "application/x-www-form-urlencoded",
                   "auth": "spark:spark"}
        params = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password
        }

        url = "%s/%s" % (self.url, "oauth/token")
        resp = requests.post(url, headers=headers, params=params)
        if resp.status_code == 200:
            resp = json.loads(resp.text)
            token = resp["access_token"]
            expiry = time.time() + (resp["expires_in"] - 30)

            self.token = token
            self.expiry = expiry
        else:
            print resp
            print resp.text

    def function(self, fun, param):
        if not self.token or not self.expiry or self.expiry > time.time():
            self._new_token()

        url = "%s/v1/devices/%s/%s" % (self.url, self.device, fun)
        headers = {"Authorization: Bearer %s" % (self.token)}
        params = {"args": param}

        resp = requests.post(url, headers=headers, params=params)
        if resp.status_code == 200:
            return True

        return False


class WhereAmI(object):
    """
    Main web app, serving out the most recent location data.
    """
    def __init__(self, settings_path="settings.json"):
        # Load settings
        self.settings = self.load_settings(settings_path)
        self.openpaths = OpenPathsAPI(
            self.settings["keys"]["openpaths"]["access"],
            self.settings["keys"]["openpaths"]["secret"]
        )

        # Read locations from configuration
        self.locations = []
        for loc in self.settings["locations"]:
            l = Location(loc["name"], loc["lat"], loc["lon"])
            self.locations.append(l)

    def load_settings(self, settings_path):
        """
        Read the application settings.

        @param settings_path Path to JSON file containing application settings.
        @returns A dictionary containing the application settings.
        """
        with open(settings_path, "r") as settings_file:
            settings = json.load(settings_file)
        return settings

    def run(self, **kwargs):
        """
        """
        pass

if __name__ == "__main__":
    W = WhereAmI()
    W.run()
