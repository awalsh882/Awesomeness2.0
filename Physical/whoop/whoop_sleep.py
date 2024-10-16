from __future__ import annotations

import os
import json
from datetime import datetime, timedelta, time
from typing import Any

from authlib.common.urls import extract_params
from authlib.integrations.requests_client import OAuth2Session
from pyairtable import Table

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
    TOKEN_ENDPOINT_AUTH_METHOD = "password_json"

    def __init__(self, username: str, password: str, authenticate: bool = True):
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
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __str__(self) -> str:
        return f"WhoopClient({self.user_id if self.user_id else '<Unauthenticated>'})"

    def close(self) -> None:
        self.session.close()

    def get_sleep_collection(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        start, end = self._format_dates(start_date, end_date)
        return self._make_paginated_request(
            method="GET",
            url_slug="v1/activity/sleep",
            params={"start": start, "end": end, "limit": 25},
        )

    def authenticate(self, **kwargs) -> None:
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
        return self.session.token is not None

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

            if next_token := response["next_token"]:
                params["nextToken"] = next_token
            else:
                break

        return response_data

    def _make_request(self, method: str, url_slug: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method=method,
            url=f"{REQUEST_URL}/{url_slug}",
            **kwargs,
        )

        response.raise_for_status()

        return response.json()

    def _format_dates(self, start_date: str | None, end_date: str | None) -> tuple[str, str]:
        end = datetime.combine(
            datetime.fromisoformat(end_date) if end_date else datetime.today(), time.max
        )
        start = datetime.combine(
            datetime.fromisoformat(start_date)
            if start_date
            else datetime.today() - timedelta(days=3),  # Fetch last 3 days to ensure no missing data
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


def check_existing_records(table: Table, record_id: str) -> bool:
    """Check if a record already exists in the Airtable table."""
    existing_records = table.all(formula=f"{{ID}} = '{record_id}'")
    return len(existing_records) > 0


def run_whoop_sleep(event, context):
    print(f"Starting function with username: {username}, AIRTABLE_API_KEY: {AIRTABLE_API_KEY}")
    client = WhoopClient(username, password)

    today = datetime.today().date()
    last_fetched = today - timedelta(days=3)  # Fetch last 3 days to ensure no missed data

    today_iso = today.isoformat()
    last_fetched_iso = last_fetched.isoformat()

    sleep_data = client.get_sleep_collection(last_fetched_iso, today_iso)

    def adjust_timezone(dt_str, offset_str):
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        hours, minutes = map(int, offset_str.split(":"))
        if "+" in offset_str:
            adjusted_dt = dt - timedelta(hours=hours, minutes=minutes)
        else:
            adjusted_dt = dt + timedelta(hours=hours, minutes=minutes)
        return adjusted_dt.isoformat()

    def convert_millis_to_duration(millis):
        return millis // 1000

    extracted_sleep_data = [
        {
            "ID": record["id"],
            "timezone_offset": record["timezone_offset"],
            "timezone_adjusted_start": adjust_timezone(record["start"], record["timezone_offset"]),
            "timezone_adjusted_end": adjust_timezone(record["end"], record["timezone_offset"]),
            "total_in_bed_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_in_bed_time_milli"]),
            "total_slow_wave_sleep_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_slow_wave_sleep_time_milli"]),
            "total_rem_sleep_time": convert_millis_to_duration(record["score"]["stage_summary"]["total_rem_sleep_time_milli"]),
            "sleep_performance_percentage": record["score"]["sleep_performance_percentage"],
            "need_from_sleep_debt": convert_millis_to_duration(record["score"]["sleep_needed"]["need_from_sleep_debt_milli"])
        }
        for record in sleep_data
    ]

    table = Table(AIRTABLE_API_KEY, BASE_ID, TABLE_NAME)

    for record in extracted_sleep_data:
        if not check_existing_records(table, record["ID"]):  # Only add if the record doesn't exist
            try:
                response = table.create(record)
                print(f"Record created: {response}")
            except Exception as e:
                print(f"Error creating record: {e}")
        else:
            print(f"Record already exists: {record['ID']}")

    print("Data uploaded successfully!")
