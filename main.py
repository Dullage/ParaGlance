#!/usr/bin/env python3

import calendar
import datetime
import json
import math
from os import environ

import requests
from flask import Flask, render_template

app = Flask(__name__)

API_KEY = environ.get("MET_OFFICE_API_KEY")

LOCATION_ID = 351611
FORECAST_CACHE_TIMEOUT = datetime.timedelta(minutes=30)


class Forecast:
    def __init__(self, api_key, location_id):
        self.api_key = api_key
        self.location_id = location_id

        self.last_refresh = datetime.datetime.utcfromtimestamp(0)

        self.data = {}

    def get(self, debug=False):
        base_url = (
            "http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json"
        )
        url = "{0}/{1}?res=3hourly&key={2}".format(
            base_url, self.location_id, self.api_key
        )

        response = requests.get(url)
        response.raise_for_status()
        self.data = response.json()

        if debug:
            with open("forecast.json", "w") as f:
                f.write(json.dumps(self.data, indent=4))

        self.last_refresh = datetime.datetime.now()

    @classmethod
    def is_not_past_date(cls, date):
        if date < datetime.date.today():
            return False
        else:
            return True

    @classmethod
    def is_not_past_time(cls, date, time_code):
        if date > datetime.date.today():
            return True

        current_minute = Forecast.current_minute()
        if (time_code + 179) > current_minute:
            return True

        else:
            return False

    @classmethod
    def convert_date(cls, date_string):
        return datetime.datetime.strptime(date_string, "%Y-%m-%dZ").date()

    @classmethod
    def is_daylight(cls, time_code):
        if time_code in ["360", "540", "720", "900", "1080"]:
            return True
        else:
            return False

    def remove_bad_date(self):
        temp_date_list = []
        for day in self.data["SiteRep"]["DV"]["Location"]["Period"]:
            date = Forecast.convert_date(day["value"])
            today = datetime.date.today()

            # Ignore Past Days
            if date < today:
                pass

            # Ignore Past Times (for current date) & Night Times
            else:
                temp_time_list = []
                for time in day["Rep"]:
                    if Forecast.is_not_past_time(
                        date, int(time["$"])
                    ) and Forecast.is_daylight(time["$"]):
                        temp_time_list.append(time)
                day["Rep"] = temp_time_list

                # Only add the date back if there are times left
                if len(temp_time_list) > 0:
                    temp_date_list.append(day)
        self.data["SiteRep"]["DV"]["Location"]["Period"] = temp_date_list

    @classmethod
    def prettify_date(cls, date):
        ordinal = lambda n: "%d%s" % (  # noqa
            n,
            "tsnrhtdd"[
                (math.floor(n / 10) % 10 != 1) * (n % 10 < 4) * n % 10:: 4
            ],
        )
        day_num = int(date.strftime("%d"))
        return str(ordinal(day_num)) + " " + date.strftime("%B")

    @classmethod
    def current_minute(cls):
        now = datetime.datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return (now - midnight).total_seconds() / 60

    @classmethod
    def date_to_day(cls, date):
        if date == datetime.date.today():
            return "Today"
        else:
            weekday = date.weekday()
            return calendar.day_name[weekday]

    @classmethod
    def format_time(cls, time_code):
        times = {
            "360": "6-9am",
            "540": "9-12pm",
            "720": "12-3pm",
            "900": "3-6pm",
            "1080": "6-9pm",
        }

        return times[time_code]

    @classmethod
    def condition(cls, code):
        conditions = {
            "NA": "Not available",
            "0": "Clear night",
            "1": "Sunny day",
            "2": "Partly cloudy",
            "3": "Partly cloudy",
            "4": "Not used",
            "5": "Mist",
            "6": "Fog",
            "7": "Cloudy",
            "8": "Overcast",
            "9": "Light rain shower",
            "10": "Light rain shower",
            "11": "Drizzle",
            "12": "Light rain",
            "13": "Heavy rain shower",
            "14": "Heavy rain shower",
            "15": "Heavy rain",
            "16": "Sleet shower",
            "17": "Sleet shower",
            "18": "Sleet",
            "19": "Hail shower",
            "20": "Hail shower",
            "21": "Hail",
            "22": "Light snow shower",
            "23": "Light snow shower",
            "24": "Light snow",
            "25": "Heavy snow shower",
            "26": "Heavy snow shower",
            "27": "Heavy snow",
            "28": "Thunder shower",
            "29": "Thunder shower",
            "30": "Thunder",
        }

        return conditions[code]

    @classmethod
    def get_site_list(cls, wind_direction):
        sites = [
            {"name": "Beachy Head", "wind_directions": ["SE"]},
            {"name": "Bo Peep", "wind_directions": ["NNE", "NE", "ENE"]},
            {"name": "Caburn", "wind_directions": ["S", "SSW", "SW"]},
            {
                "name": "Devils Dyke",
                "wind_directions": ["N", "WNW", "NW", "NNW"],
            },
            {"name": "Ditchling", "wind_directions": ["N", "NNE", "NNW"]},
            {"name": "Firle", "wind_directions": ["N", "NNE", "NW", "NNW"]},
            {"name": "High & Over", "wind_directions": ["E"]},
            {
                "name": "Newhaven Cliffs",
                "wind_directions": ["SSE", "S", "SSW"],
            },
            {"name": "Truleigh", "wind_directions": ["N", "NNE", "NNW"]},
        ]

        return_sites = []
        for site in sites:
            if wind_direction in site["wind_directions"]:
                return_sites.append(site)

        return return_sites

    @classmethod
    def classify(cls, attribute, value):
        neg = "negative"
        pos = "positive"

        # Wind Direction
        if attribute == "wind_direction":
            if value not in ["W", "WSW"]:
                return pos
            else:
                return neg

        # Wind Speed
        elif attribute == "wind_speed":
            if 4 <= value <= 13:
                return pos
            else:
                return neg

        # Gust Strength
        elif attribute == "gust_strength":
            if value <= 15:
                return pos
            else:
                return neg

        # Gust Difference
        elif attribute == "gust_difference":
            if value <= 5:
                return pos
            else:
                return neg

        # Conditions
        elif attribute == "conditions":
            if value <= 8:
                return pos
            else:
                return neg


forecast = Forecast(API_KEY, LOCATION_ID)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get-forecast")
def get_forecast():
    if (
        forecast.last_refresh
        < datetime.datetime.now() - FORECAST_CACHE_TIMEOUT
    ):
        forecast.get(debug=True)
        forecast.remove_bad_date()

    return render_template("forecast.html", forecast=forecast)
