#! /usr/bin/env python

"""
Simple Python script to interact with Spark and OpenPaths APIs.
"""

import math
import oauth2
import os
import requests
import simplejson as json
import spyrk
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
        last_loc = self.get({"num_points": 1})[0]
        return Location("last_location", last_loc["lat"], last_loc["lon"])


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
        self.spark = spyrk.SparkCloud(
            self.settings["keys"]["spark"]["username"],
            self.settings["keys"]["spark"]["password"]
        )
        self.device = self.spark.devices["Ron"]

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
        Check for last-known location and update the clock hand, and then
        sleep for 5 minutes.
        """
        while True:
            last_known = self.openpaths.get_last_location()
            loc_name = None
            for location in self.locations:
                if location.is_near(last_known, 800):  # Half a mile
                    loc_name = location.name

            if not loc_name:
                loc_name = "TRAVELLING"

            self.device.new_location(loc_name)
            time.sleep(300)

if __name__ == "__main__":
    print(os.getpid())
    W = WhereAmI()
    W.run()
