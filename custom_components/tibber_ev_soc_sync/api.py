"""Minimal client for the Tibber app API (app.tibber.com).

This is the unofficial API used by the Tibber app itself. Tibber's public API is
read-only, but the app lets you set the battery level of vehicles that Tibber has
no direct integration with ("offline" vehicles). This client does exactly that.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)

LOGIN_URL = "https://app.tibber.com/login.credentials"
GQL_URL = "https://app.tibber.com/v4/gql"
TIMEOUT = ClientTimeout(total=20)

BATTERY_LEVEL_SETTING = "offline.vehicle.batteryLevel"

QUERY_ACCOUNT = "{ me { homes { id title } myVehicles { vehicles { id title } } } }"
MUTATION_SET_VEHICLE_SETTINGS = (
    "mutation SetVehicleSettings($vehicleId: String!, $homeId: String!, "
    "$settings: [SettingsItemInput!]) { me { setVehicleSettings(id: $vehicleId, "
    "homeId: $homeId, settings: $settings) { __typename } } }"
)


class TibberAppError(Exception):
    """Generic error talking to the Tibber app API."""


class TibberAppAuthError(TibberAppError):
    """Login failed (wrong e-mail/password or account locked)."""


@dataclass(frozen=True)
class TibberHome:
    """A home on the Tibber account."""

    id: str
    title: str


@dataclass(frozen=True)
class TibberVehicle:
    """A vehicle on the Tibber account."""

    id: str
    title: str


@dataclass(frozen=True)
class TibberAccount:
    """Homes and vehicles on the Tibber account."""

    homes: list[TibberHome]
    vehicles: list[TibberVehicle]


class TibberAppClient:
    """Talks to app.tibber.com. Logs in for every operation (they are rare)."""

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password

    async def async_login(self) -> str:
        """Log in and return a bearer token."""
        try:
            async with self._session.post(
                LOGIN_URL,
                data={"email": self._email, "password": self._password},
                timeout=TIMEOUT,
            ) as response:
                if response.status in (400, 401, 403):
                    raise TibberAppAuthError(f"Login rejected ({response.status})")
                if response.status != 200:
                    raise TibberAppError(f"Login failed ({response.status})")
                payload = await response.json(content_type=None)
        except ClientError as err:
            raise TibberAppError(f"Could not reach Tibber: {err}") from err

        token = payload.get("token") if isinstance(payload, dict) else None
        if not token:
            raise TibberAppAuthError("Login returned no token")
        return token

    async def _async_gql(self, token: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with self._session.post(
                GQL_URL,
                json={"query": query, "variables": variables or {}},
                headers={"Authorization": f"Bearer {token}"},
                timeout=TIMEOUT,
            ) as response:
                if response.status in (401, 403):
                    raise TibberAppAuthError(f"Not authorised ({response.status})")
                if response.status != 200:
                    raise TibberAppError(f"Tibber responded {response.status}")
                payload = await response.json(content_type=None)
        except ClientError as err:
            raise TibberAppError(f"Could not reach Tibber: {err}") from err

        if not isinstance(payload, dict):
            raise TibberAppError("Unexpected response from Tibber")
        if errors := payload.get("errors"):
            messages = "; ".join(str(error.get("message", error)) for error in errors)
            if "auth" in messages.lower():
                raise TibberAppAuthError(messages)
            raise TibberAppError(messages)
        return payload.get("data") or {}

    async def async_get_account(self) -> TibberAccount:
        """Return the homes and vehicles on the account."""
        token = await self.async_login()
        data = await self._async_gql(token, QUERY_ACCOUNT)
        return parse_account(data)

    async def async_set_battery_level(self, home_id: str, vehicle_id: str, level: int) -> None:
        """Set the battery level (0–100 %) of an offline vehicle."""
        if not 0 <= level <= 100:
            raise ValueError(f"Battery level out of range: {level}")
        token = await self.async_login()
        data = await self._async_gql(
            token,
            MUTATION_SET_VEHICLE_SETTINGS,
            {
                "vehicleId": vehicle_id,
                "homeId": home_id,
                "settings": [{"key": BATTERY_LEVEL_SETTING, "value": level}],
            },
        )
        result = (data.get("me") or {}).get("setVehicleSettings")
        if not result:
            raise TibberAppError("Tibber did not confirm the new battery level")
        _LOGGER.debug("Battery level %s %% sent for vehicle %s", level, vehicle_id)


def parse_account(data: dict[str, Any]) -> TibberAccount:
    """Parse the response of QUERY_ACCOUNT."""
    me = data.get("me") or {}
    homes = [
        TibberHome(id=home["id"], title=home.get("title") or home["id"])
        for home in me.get("homes") or []
        if home and home.get("id")
    ]
    vehicles = [
        TibberVehicle(id=vehicle["id"], title=vehicle.get("title") or vehicle["id"])
        for vehicle in ((me.get("myVehicles") or {}).get("vehicles") or [])
        if vehicle and vehicle.get("id")
    ]
    return TibberAccount(homes=homes, vehicles=vehicles)
