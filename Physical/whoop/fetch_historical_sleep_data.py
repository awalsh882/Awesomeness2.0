from __future__ import annotations

import os
import json
from datetime import datetime, timedelta, time
from typing import Any
from dotenv import load_dotenv  # Add this import
from authlib.common.urls import extract_params
from authlib.integrations.requests_client import OAuth2Session
import pandas as pd

load_dotenv()

# Replace with your WHOOP credentials
username = os.getenv("USERNAME") or ""
password = os.getenv("PASSWORD") or ""

AUTH_URL = "https://api-7.whoop.com"
REQUEST_URL = "https://api.prod.whoop.com/developer"

# Authentication helper
def _auth_password_json(_client, _method, uri, headers, body):
    body = json.dumps(dict(extract_params(body)))
    headers["Content-Type"] = "application/json"
    return uri, headers, body

# Define the adjust_timezone function
def adjust_timezone(dt_str, offset_str):
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    hours, minutes = map(int, offset_str.split(":"))
    if "+" in offset_str:
        adjusted_dt = dt - timedelta(hours=hours, minutes=minutes)
    else:
        adjusted_dt = dt + timedelta(hours=hours, minutes=minutes)
    return adjusted_dt.isoformat()

# WhoopClient class for interacting with the WHOOP API
class WhoopClient:
    TOKEN_ENDPOINT_AUTH_METHOD = "password_json"

    def __init__(self, username: str, password: str, authenticate: bool = True):
        self._username = username
        self._password = password

        # OAuth2 session
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
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __str__(self) -> str:
        return f"WhoopClient({self.user_id if self.user_id else '<Unauthenticated>'})"

    def close(self) -> None:
        self.session.close()

    def authenticate(self, **kwargs) -> None:
        token = self.session.fetch_token(
            url=f"{AUTH_URL}/oauth/token",
            username=self._username,
            password=self._password,
            grant_type="password",
            **kwargs,
        )

        if 'access_token' in token:
            self.session.token = token  # Store the token if available
        else:
            raise Exception("Authentication failed. Access token not found.")
            
        # Fetch and store the user ID if not already set
        if not self.user_id:
            self.user_id = str(self.session.token.get("user", {}).get("id", ""))

    def get_sleep_collection(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        start, end = self._format_dates(start_date, end_date)
        return self._make_paginated_request(
            method="GET",
            url_slug="v1/activity/sleep",
            params={"start": start, "end": end, "limit": 25},
        )

    def _make_paginated_request(self, method, url_slug, **kwargs) -> list[dict[str, Any]]:
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

            if next_token := response.get("next_token"):
                params["nextToken"] = next_token
            else:
                break

        return response_data

    def _make_request(self, method: str, url_slug: str, **kwargs: Any) -> dict[str, Any]:
        print(f"Making request to: {REQUEST_URL}/{url_slug} with params: {kwargs.get('params')}")
        response = self.session.request(
            method=method,
            url=f"{REQUEST_URL}/{url_slug}",
            **kwargs,
        )
        
        # Print the full response content for debugging
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content}")
        
        response.raise_for_status()

        return response.json()

    def _format_dates(self, start_date: str | None, end_date: str | None) -> tuple[str, str]:
        end = datetime.combine(
            datetime.fromisoformat(end_date) if end_date else datetime.today(), time.max
        )
        start = datetime.combine(
            datetime.fromisoformat(start_date)
            if start_date
            else datetime.today() - timedelta(days=365),  # Fetch last 12 months of data
            time.min,
        )

        if start > end:
            raise ValueError(
                f"Start datetime greater than end datetime: {start} > {end}"
            )

        return (
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

def fetch_and_save_sleep_data():
    print(f"Starting function with username: {username}")

    client = WhoopClient(username, password)

    # Fetch sleep data for the past 12 months
    today = datetime.today().date()
    last_year = today - timedelta(days=300)

    today_iso = today.isoformat()
    last_year_iso = last_year.isoformat()

    sleep_data = client.get_sleep_collection(last_year_iso, today_iso)

    def convert_millis_to_duration(millis):
        return millis // 1000

    extracted_sleep_data = [
        {
            "ID": record["id"],
            "timezone_offset": record["timezone_offset"],  # Add timezone offset
            "timezone_adjusted_start": adjust_timezone(record["start"], record["timezone_offset"]),  # Already present
            "timezone_adjusted_end": adjust_timezone(record["end"], record["timezone_offset"]),  # Already present
            "total_in_bed_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_in_bed_time_milli"]),
            "total_slow_wave_sleep_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_slow_wave_sleep_time_milli"]),
            "total_rem_sleep_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_rem_sleep_time_milli"]),
            "sleep_performance_percentage": record["score"]["sleep_performance_percentage"],
            "need_from_sleep_debt": convert_millis_to_duration(record["score"]["sleep_needed"]["need_from_sleep_debt_milli"])
        }
        for record in sleep_data
    ]

    # Convert data to DataFrame and save as CSV
    df = pd.DataFrame(extracted_sleep_data)
    output_file = "whoop_sleep_data.csv"
    df.to_csv(output_file, index=False)
    print(f"Data successfully saved to {output_file}")

# Run the function
if __name__ == "__main__":
    fetch_and_save_sleep_data()
