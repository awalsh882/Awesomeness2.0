"""Tools for acquiring and analyzing Whoop API data.

WHOOP is a wearable strap for monitoring sleep, activity, and workouts. Learn more about
WHOOP at https://www.whoop.com.

WHOOP API documentation can be found at https://developer.whoop.com/api.

"""

from __future__ import annotations

import os
import json
from datetime import datetime, time, timedelta
from typing import Any

from dotenv import load_dotenv
from authlib.common.urls import extract_params
from authlib.integrations.requests_client import OAuth2Session
from pyairtable import Table

import whoop as wh
import pandas as pd

load_dotenv()

username = os.getenv("USERNAME") or ""
password = os.getenv("PASSWORD") or ""
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

AUTH_URL = "https://api-7.whoop.com"
REQUEST_URL = "https://api.prod.whoop.com/developer"

def _auth_password_json(_client, _method, uri, headers, body):
    body = json.dumps(dict(extract_params(body)))
    headers["Content-Type"] = "application/json"
    return uri, headers, body

class WhoopClient:
    """Make requests to the WHOOP API.

    Attributes:
        session (authlib.OAuth2Session): Requests session for accessing the WHOOP API.
        user_id (str): User ID of the owner of the session. Will default to an empty
            string before the session is authenticated and then replaced by the correct
            user ID once a token is fetched.

    Raises:
        ValueError: If `start_date` is after `end_date`.
    """

    TOKEN_ENDPOINT_AUTH_METHOD = "password_json"  # noqa

    ####################################################################################
    # INIT STUFF

    def __init__(
        self,
        username: str,
        password: str,
        authenticate: bool = True,
    ):
        """Initialize an OAuth2 session for making API requests.

        Optionally makes a request to the WHOOP API to acquire an access token.

        Args:
            username (str): WHOOP account email.
            password (str): WHOOP account password.
            authenticate (bool): Whether to fetch a token from the API upon
                session creation. If false, `authenticate()` must be called manually.
                Defaults to true.
            kwargs (dict[str, Any], optional): Additional arguments for OAuth2Session.
        """
        self._username = username
        self._password = password

        self.session = OAuth2Session(
            token_endpoint=f"{AUTH_URL}/oauth/token",
            token_endpoint_auth_method=self.TOKEN_ENDPOINT_AUTH_METHOD,
        )

        self.session.register_client_auth_method(
            (self.TOKEN_ENDPOINT_AUTH_METHOD, _auth_password_json)
        )

        self.user_id = ""

        if authenticate:
            self.authenticate()

    def __enter__(self) -> WhoopClient:
        """Enter a context manager.

        Returns:
            WhoopClient: A WHOOP client with an active OAuth2Session.
        """
        return self

    def __exit__(self, *_) -> None:
        """Exit a context manager by closing the OAuth2 session.

        Args:
            _ (Any): Exception arguments passed when closing context manager.
        """
        self.close()

    def __str__(self) -> str:
        """Generate string representation of client.

        Returns:
            str: String representation of client featuring user ID of the owner of the
                session.
        """
        return f"WhoopClient({self.user_id if self.user_id else '<Unauthenticated>'})"

    def close(self) -> None:
        """Close the OAuth2 Session."""
        self.session.close()

    ####################################################################################
    # API ENDPOINTS

    def get_cycle_collection(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Make request to Get Cycle Collection endpoint.

        Get all physiological cycles for a user. Results are sorted by start time in
        descending order.

        Returns:
            list[dict[str, Any]]: Response JSON data loaded into an object. Example:
                [
                    {
                        "id": 93845,
                        "user_id": 10129,
                        "created_at": "2022-04-24T11:25:44.774Z",
                        "updated_at": "2022-04-24T14:25:44.774Z",
                        "start": "2022-04-24T02:25:44.774Z",
                        "end": "2022-04-24T10:25:44.774Z",
                        "timezone_offset": "-05:00",
                        "score_state": "SCORED",
                        "score": {
                            "strain": 5.2951527,
                            "kilojoule": 8288.297,
                            "average_heart_rate": 68,
                            "max_heart_rate": 141
                        }
                    },
                    ...
                ]
        """
        start, end = self._format_dates(start_date, end_date)

        return self._make_paginated_request(
            method="GET",
            url_slug="v1/cycle",
            params={"start": start, "end": end, "limit": 25},
        )

    def get_recovery_for_cycle(self, cycle_id: str) -> dict[str, Any]:
        """Make request to Get Recovery For Cycle endpoint.

        Get the recovery for a cycle.

        Returns:
            dict[str, Any]: Response JSON data loaded into an object. Example:
                {
                    "cycle_id": 93845,
                    "sleep_id": 10235,
                    "user_id": 10129,
                    "created_at": "2022-04-24T11:25:44.774Z",
                    "updated_at": "2022-04-24T14:25:44.774Z",
                    "score_state": "SCORED",
                    "score": {
                        "user_calibrating": False,
                        "recovery_score": 44,
                        "resting_heart_rate": 64,
                        "hrv_rmssd_milli": 31.813562,
                        "spo2_percentage": 95.6875,
                        "skin_temp_celsius": 33.7
                    }
                }
        """
        return self._make_request(
            method="GET", url_slug=f"v1/cycle/{cycle_id}/recovery"
        )

    def get_sleep_collection(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Make request to Get Sleep Collection endpoint.

        Get all sleeps for a user. Results are sorted by start time in descending order.

        Returns:
            list[dict[str, Any]]: Response JSON data loaded into an object. Example:
                [
                    {
                        "id": 93845,
                        "user_id": 10129,
                        "created_at": "2022-04-24T11:25:44.774Z",
                        "updated_at": "2022-04-24T14:25:44.774Z",
                        "start": "2022-04-24T02:25:44.774Z",
                        "end": "2022-04-24T10:25:44.774Z",
                        "timezone_offset": "-05:00",
                        "nap": False,
                        "score_state": "SCORED",
                        "score": {
                            "stage_summary": {},
                            "sleep_needed": {},
                            "respiratory_rate": 16.11328125,
                            "sleep_performance_percentage": 98,
                            "sleep_consistency_percentage": 90,
                            "sleep_efficiency_percentage": 91.69533848
                        }
                    },
                    ...
                ]
        """
        start, end = self._format_dates(start_date, end_date)

        return self._make_paginated_request(
            method="GET",
            url_slug="v1/activity/sleep",
            params={"start": start, "end": end, "limit": 25},
        )

    def get_workout_collection(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Make request to Get Workout Collection endpoint.

        Get all workouts for a user. Results are sorted by start time in descending
        order.

        Returns:
            list[dict[str, Any]]: Response JSON data loaded into an object. Example:
                [
                    {
                        "id": 1043,
                        "user_id": 9012,
                        "created_at": "2022-04-24T11:25:44.774Z",
                        "updated_at": "2022-04-24T14:25:44.774Z",
                        "start": "2022-04-24T02:25:44.774Z",
                        "end": "2022-04-24T10:25:44.774Z",
                        "timezone_offset": "-05:00",
                        "sport_id": 1,
                        "score_state": "SCORED",
                        "score": {
                            "strain": 8.2463,
                            "average_heart_rate": 123,
                            "max_heart_rate": 146,
                            "kilojoule": 1569.34033203125,
                            "percent_recorded": 100,
                            "distance_meter": 1772.77035916,
                            "altitude_gain_meter": 46.64384460449,
                            "altitude_change_meter": -0.781372010707855,
                            "zone_duration": {}
                        }
                    },
                    ...
                ]
        """
        start, end = self._format_dates(start_date, end_date)

        return self._make_paginated_request(
            method="GET",
            url_slug="v1/activity/workout",
            params={"start": start, "end": end, "limit": 25},
        )

    ####################################################################################
    # API HELPER METHODS

    def authenticate(self, **kwargs) -> None:
        """Authenticate OAuth2Session by fetching token.

        If `user_id` is `None`, it will be set according to the `user_id` returned with
        the token.

        Args:
            kwargs (dict[str, Any], optional): Additional arguments for `fetch_token()`.
        """
        self.session.fetch_token(
            url=f"{AUTH_URL}/oauth/token",
            username=self._username,
            password=self._password,
            grant_type="password",
            **kwargs,
        )

        if not self.user_id:
            self.user_id = str(self.session.token.get("user", {}).get("id", ""))

    def is_authenticated(self) -> bool:
        """Check if the OAuth2Session is authenticated.

        Returns:
            bool: Whether the OAuth2Session has a token and is therefore authenticated.
        """
        return self.session.token is not None

    def _make_paginated_request(
        self, method, url_slug, **kwargs
    ) -> list[dict[str, Any]]:
        params = kwargs.pop("params", {})
        response_data: list[dict[str, Any]] = []

        while True:
            response = self._make_request(
                method=method,
                url_slug=url_slug,
                params=params,
                **kwargs,
            )

            response_data += response["records"]

            if next_token := response["next_token"]:
                params["nextToken"] = next_token

            else:
                break

        return response_data

    def _make_request(
        self, method: str, url_slug: str, **kwargs: Any
    ) -> dict[str, Any]:
        response = self.session.request(
            method=method,
            url=f"{REQUEST_URL}/{url_slug}",
            **kwargs,
        )

        response.raise_for_status()

        return response.json()

    def _format_dates(
        self, start_date: str | None, end_date: str | None
    ) -> tuple[str, str]:
        end = datetime.combine(
            datetime.fromisoformat(end_date) if end_date else datetime.today(), time.max
        )
        start = datetime.combine(
            datetime.fromisoformat(start_date)
            if start_date
            else datetime.today() - timedelta(days=6),
            time.min,
        )

        if start > end:
            raise ValueError(
                f"Start datetime greater than end datetime: {start} > {end}"
            )

        return (
            start.isoformat() + "Z",
            end.isoformat(timespec="seconds") + "Z",
        )


client = wh.WhoopClient(username, password)

# Get today's date and yesterday's date
today = datetime.today().date()
yesterday = today - timedelta(days=4)


# Convert dates to ISO format strings
today_iso = today.isoformat()
yesterday_iso = yesterday.isoformat()

sleep_data = client.get_sleep_collection(yesterday_iso, today_iso)
recovery = client.get_recovery_collection()

def adjust_timezone(dt_str, offset_str):
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    hours, minutes = map(int, offset_str.split(":"))
    if "+" in offset_str:
        adjusted_dt = dt - timedelta(hours=hours, minutes=minutes)
    else:
        adjusted_dt = dt + timedelta(hours=hours, minutes=minutes)
    return adjusted_dt.isoformat()

def convert_millis_to_duration(millis):
    seconds = millis // 1000
    return seconds


# Extract only the 'start' and 'end' fields
extracted_sleep_data = [{
    "ID": record["id"],
    "timezone_offset": record["timezone_offset"],
    "timezone_adjusted_start": adjust_timezone(record["start"], record["timezone_offset"]),
    "timezone_adjusted_end": adjust_timezone(record["end"], record["timezone_offset"]),
    "total_in_bed_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_in_bed_time_milli"]),
    "total_slow_wave_sleep_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_slow_wave_sleep_time_milli"]),
    "total_rem_sleep_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_rem_sleep_time_milli"]),
    "sleep_performance_percentage": record["score"]["sleep_performance_percentage"]
} for record in sleep_data]

print(json.dumps(extracted_sleep_data, indent=4))

# Initialize Airtable table
table = Table(AIRTABLE_API_KEY, BASE_ID, TABLE_NAME)

# Upload the data to Airtable
for record in extracted_sleep_data:
    try:
        response = table.create(record)
        print(f"Record created: {response}")
    except Exception as e:
        print(f"Error creating record: {e}")

print("Data uploaded successfully!")