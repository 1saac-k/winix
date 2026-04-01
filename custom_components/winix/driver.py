"""Winix device driver."""

from __future__ import annotations

from enum import Enum, unique

import aiohttp

from .const import (
    AIRFLOW_HIGH,
    AIRFLOW_LOW,
    AIRFLOW_MEDIUM,
    AIRFLOW_SLEEP,
    AIRFLOW_TURBO,
    ATTR_AIRFLOW,
    ATTR_BRIGHTNESS_LEVEL,
    ATTR_CHILD_LOCK,
    ATTR_CURRENT_HUMIDITY,
    ATTR_MODE,
    ATTR_PLASMA,
    ATTR_POWER,
    ATTR_TARGET_HUMIDITY,
    ATTR_TIMER,
    ATTR_UV_SANITIZE,
    ATTR_WATER_BUCKET,
    LOGGER,
    MODE_AUTO,
    MODE_CLOTHES,
    MODE_CONTINUOUS,
    MODE_MANUAL,
    MODE_QUIET,
    MODE_SHOES,
    OFF_DRY_VALUE,
    OFF_VALUE,
    ON_VALUE,
)


@unique
class BrightnessLevel(Enum):
    """Brightness levels."""

    Level0 = 0
    Level1 = 30
    Level2 = 70
    Level3 = 100


class WinixDevice:
    """Base Winix device driver."""

    # pylint: disable=line-too-long
    CTRL_URL = "https://us.api.winix-iot.com/common/control/devices/{deviceid}/A211/{attribute}:{value}"
    STATE_URL = "https://us.api.winix-iot.com/common/event/sttus/devices/{deviceid}"

    category_keys: dict[str, str] | None = None
    state_keys: dict[str, dict[str, str]] | None = None

    def __init__(self, device_id: str, client: aiohttp.ClientSession) -> None:
        """Create an instance of WinixDevice."""
        self.device_id = device_id
        self._client = client

    async def _rpc_attr(self, attr: str, value: str) -> None:
        """Make a raw API call with the given attribute code and value."""
        LOGGER.debug("_rpc_attr attribute=%s, value=%s", attr, value)
        resp = await self._client.get(
            self.CTRL_URL.format(deviceid=self.device_id, attribute=attr, value=value),
            raise_for_status=True,
        )
        raw_resp = await resp.text()
        LOGGER.debug("_rpc_attr response=%s", raw_resp)

    async def control(self, category: str, state: str) -> None:
        """Control the device using semantic category/state names."""
        await self._rpc_attr(
            self.category_keys[category],
            self.state_keys[category][state],
        )

    async def get_state(self) -> dict[str, str | int]:
        """Get device state."""

        url = self.STATE_URL.format(deviceid=self.device_id)
        response = await self._client.get(url)
        if response.status != 200:
            LOGGER.error("Error getting data, status code %s", response.status)
            return {}

        json = await response.json()

        # pylint: disable=pointless-string-statement
        """
        {
            'statusCode': 200,
            'headers': {'resultCode': 'S100', 'resultMessage': ''},
            'body': {
                'deviceId': '847207352CE0_364yr8i989', 'totalCnt': 1,
                'data': [
                    {
                        'apiNo': 'A210', 'apiGroup': '001', 'deviceGroup': 'Air01', 'modelId': 'C545',
                        'attributes': {'A02': '0', 'A03': '01', 'A04': '01', 'A05': '01', 'A07': '0', 'A21': '1257', 'S07': '01', 'S08': '74', 'S14': '121'},
                        'rssi': '-55', 'creationTime': 1673449200634, 'utcDatetime': '2023-01-11 15:00:00', 'utcTimestamp': 1673449200
                    }
                ]
            }
        }

        Another sample from https://github.com/iprak/winix/issues/98
        {'statusCode': 200, 'headers': {'resultCode': 'S100', 'resultMessage': 'no data'}, 'body': {}}
        """

        headers = json.get("headers", {})
        if headers.get("resultMessage") == "no data":
            LOGGER.info("No data received")
            return {}

        output = {}

        try:
            LOGGER.debug(json)
            payload = json["body"]["data"][0]["attributes"]
        except Exception as err:  # pylint: disable=broad-except # noqa: BLE001
            LOGGER.error("Error parsing response json, received %s", json, exc_info=err)

            # Return empty object so that callers don't crash (#37)
            return output

        for payload_key, attribute in payload.items():
            for category, local_key in self.category_keys.items():
                if payload_key == local_key:
                    # pylint: disable=consider-iterating-dictionary
                    if category in self.state_keys:
                        for value_key, value in self.state_keys[category].items():
                            if attribute == value:
                                output[category] = value_key
                    else:
                        output[category] = int(attribute)

        return output


# Alias for backward compatibility
WinixDriver = WinixDevice


class AirPurifierDevice(WinixDevice):
    """Winix Air Purifier driver."""

    # pylint: disable=line-too-long
    PARAM_URL = "https://us.api.winix-iot.com/common/event/param/devices/{deviceid}"

    category_keys = {
        ATTR_POWER: "A02",
        ATTR_MODE: "A03",
        ATTR_AIRFLOW: "A04",
        "aqi": "A05",
        ATTR_PLASMA: "A07",
        ATTR_CHILD_LOCK: "A08",
        ATTR_BRIGHTNESS_LEVEL: "A16",
        "filter_hour": "A21",
        "air_quality": "S07",
        "air_qvalue": "S08",
        "ambient_light": "S14",
    }

    state_keys = {
        ATTR_POWER: {OFF_VALUE: "0", ON_VALUE: "1"},
        ATTR_MODE: {MODE_AUTO: "01", MODE_MANUAL: "02"},
        ATTR_AIRFLOW: {
            AIRFLOW_LOW: "01",
            AIRFLOW_MEDIUM: "02",
            AIRFLOW_HIGH: "03",
            AIRFLOW_TURBO: "05",
            AIRFLOW_SLEEP: "06",
        },
        ATTR_CHILD_LOCK: {OFF_VALUE: "0", ON_VALUE: "1"},
        ATTR_PLASMA: {OFF_VALUE: "0", ON_VALUE: "1"},
        "air_quality": {"good": "01", "fair": "02", "poor": "03"},
    }

    async def turn_on(self) -> None:
        """Turn the device on."""
        await self.control(ATTR_POWER, ON_VALUE)

    async def turn_off(self) -> None:
        """Turn the device off."""
        await self.control(ATTR_POWER, OFF_VALUE)

    async def auto(self) -> None:
        """Set device in auto mode."""
        await self.control(ATTR_MODE, MODE_AUTO)

    async def manual(self) -> None:
        """Set device in manual mode."""
        await self.control(ATTR_MODE, MODE_MANUAL)

    async def plasmawave_on(self) -> None:
        """Turn plasmawave on."""
        await self.control(ATTR_PLASMA, ON_VALUE)

    async def plasmawave_off(self) -> None:
        """Turn plasmawave off."""
        await self.control(ATTR_PLASMA, OFF_VALUE)

    async def low(self) -> None:
        """Set speed low."""
        await self.control(ATTR_AIRFLOW, AIRFLOW_LOW)

    async def medium(self) -> None:
        """Set speed medium."""
        await self.control(ATTR_AIRFLOW, AIRFLOW_MEDIUM)

    async def high(self) -> None:
        """Set speed high."""
        await self.control(ATTR_AIRFLOW, AIRFLOW_HIGH)

    async def turbo(self) -> None:
        """Set speed turbo."""
        await self.control(ATTR_AIRFLOW, AIRFLOW_TURBO)

    async def sleep(self) -> None:
        """Set device in sleep mode."""
        await self.control(ATTR_AIRFLOW, AIRFLOW_SLEEP)

    async def set_brightness_level(self, value: int) -> bool:
        """Set brightness level."""
        if not any(e.value == value for e in BrightnessLevel):
            return False

        await self._rpc_attr(self.category_keys[ATTR_BRIGHTNESS_LEVEL], str(value))
        return True

    async def get_filter_life(self) -> int | None:
        """Get the total filter life."""
        response = await self._client.get(
            self.PARAM_URL.format(deviceid=self.device_id)
        )
        if response.status != 200:
            LOGGER.error("Error getting filter life, status code %s", response.status)
            return None

        json = await response.json()

        # pylint: disable=pointless-string-statement
        """
        {
            'statusCode': 200, 'headers': {'resultCode': 'S100', 'resultMessage': ''},
            'body': {
                'deviceId': '847207352CE0_364yr8i989', 'totalCnt': 1,
                'data': [
                    {
                        'apiNo': 'A240', 'apiGroup': '004', 'modelId': 'C545', 'attributes': {'P01': '6480'}
                    }
                ]
            }
        }
        """

        headers = json.get("headers", {})
        if headers.get("resultMessage") == "no data":
            LOGGER.info("No filter life data received")
            return None

        try:
            attributes = json["body"]["data"][0]["attributes"]
            if attributes:
                return int(attributes["P01"])
        except Exception:  # pylint: disable=broad-except # noqa: BLE001
            return None


class DehumidifierDevice(WinixDevice):
    """Winix Dehumidifier driver."""

    category_keys = {
        ATTR_POWER: "D02",
        ATTR_MODE: "D03",
        ATTR_AIRFLOW: "D04",
        ATTR_TARGET_HUMIDITY: "D05",
        ATTR_CHILD_LOCK: "D08",
        ATTR_CURRENT_HUMIDITY: "D10",
        ATTR_WATER_BUCKET: "D11",
        ATTR_UV_SANITIZE: "D13",
        ATTR_TIMER: "D15",
    }

    state_keys = {
        ATTR_POWER: {
            OFF_VALUE: "0",
            ON_VALUE: "1",
            OFF_DRY_VALUE: "2",
        },
        ATTR_MODE: {
            MODE_AUTO: "01",
            MODE_MANUAL: "02",
            MODE_CLOTHES: "03",
            MODE_SHOES: "04",
            MODE_QUIET: "05",
            MODE_CONTINUOUS: "06",
        },
        ATTR_AIRFLOW: {
            AIRFLOW_HIGH: "01",
            AIRFLOW_LOW: "02",
            AIRFLOW_TURBO: "03",
        },
        ATTR_CHILD_LOCK: {
            OFF_VALUE: "0",
            ON_VALUE: "1",
        },
        ATTR_WATER_BUCKET: {
            OFF_VALUE: "0",  # not full
            ON_VALUE: "1",  # full or bucket detached
        },
        ATTR_UV_SANITIZE: {
            OFF_VALUE: "0",
            ON_VALUE: "1",
        },
    }

    async def turn_on(self) -> None:
        """Turn the device on."""
        await self.control(ATTR_POWER, ON_VALUE)

    async def turn_off(self) -> None:
        """Turn the device off."""
        await self.control(ATTR_POWER, OFF_VALUE)

    async def set_mode(self, mode: str) -> None:
        """Set operating mode."""
        await self.control(ATTR_MODE, mode)

    async def set_fan_speed(self, speed: str) -> None:
        """Set fan speed."""
        await self.control(ATTR_AIRFLOW, speed)

    async def set_humidity(self, humidity: int) -> None:
        """Set target humidity."""
        await self._rpc_attr(self.category_keys[ATTR_TARGET_HUMIDITY], str(humidity))

    async def set_child_lock(self, locked: bool) -> None:
        """Set child lock state."""
        await self.control(ATTR_CHILD_LOCK, ON_VALUE if locked else OFF_VALUE)

    async def set_uv_sanitize(self, enabled: bool) -> None:
        """Set UV sanitize state."""
        await self.control(ATTR_UV_SANITIZE, ON_VALUE if enabled else OFF_VALUE)

    async def set_timer(self, hours: int) -> None:
        """Set timer in hours (0 to disable)."""
        await self._rpc_attr(self.category_keys[ATTR_TIMER], str(hours))


class AirConditionerDevice(WinixDevice):
    """Winix Air Conditioner driver (placeholder, packet format TBD)."""

    category_keys = {}
    state_keys = {}
