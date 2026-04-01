"""Winix Dehumidifier entity."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.humidifier import (
    DOMAIN as HUMIDIFIER_DOMAIN,
    HumidifierAction,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WINIX_DOMAIN
from .const import (
    ATTR_AIRFLOW,
    ATTR_CURRENT_HUMIDITY,
    ATTR_FILTER_REPLACEMENT_DATE,
    ATTR_LOCATION,
    ATTR_MODE,
    ATTR_POWER,
    ATTR_TARGET_HUMIDITY,
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
    WINIX_DATA_COORDINATOR,
)
from .device_wrapper import WinixDeviceWrapper
from .manager import WinixEntity, WinixManager

DEHUMIDIFIER_MIN_HUMIDITY = 35
DEHUMIDIFIER_MAX_HUMIDITY = 70
DEHUMIDIFIER_HUMIDITY_STEP = 5

DEHUMIDIFIER_MODES = [
    MODE_AUTO,
    MODE_MANUAL,
    MODE_CLOTHES,
    MODE_SHOES,
    MODE_QUIET,
    MODE_CONTINUOUS,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winix dehumidifier entities."""
    data = hass.data[WINIX_DOMAIN][entry.entry_id]
    manager: WinixManager = data[WINIX_DATA_COORDINATOR]
    entities = [
        WinixDehumidifier(wrapper, manager)
        for wrapper in manager.get_device_wrappers()
        if hasattr(wrapper._driver, "set_mode")  # only dehumidifier devices
    ]
    async_add_entities(entities)
    LOGGER.info("Added %s Winix dehumidifiers", len(entities))


class WinixDehumidifier(WinixEntity, HumidifierEntity):
    """Representation of a Winix Dehumidifier."""

    # https://developers.home-assistant.io/docs/core/entity/humidifier/
    _attr_supported_features = HumidifierEntityFeature.MODES

    _attr_min_humidity = DEHUMIDIFIER_MIN_HUMIDITY
    _attr_max_humidity = DEHUMIDIFIER_MAX_HUMIDITY

    def __init__(self, wrapper: WinixDeviceWrapper, coordinator: WinixManager) -> None:
        """Initialize the dehumidifier entity."""
        super().__init__(wrapper, coordinator)
        self._attr_unique_id = f"{HUMIDIFIER_DOMAIN}.{WINIX_DOMAIN}_{self._mac}"

    @property
    def name(self) -> str | None:
        """Return None so this is treated as the primary device entity."""
        return None

    @property
    def available_modes(self) -> list[str]:
        """Return the list of available modes."""
        return DEHUMIDIFIER_MODES

    @property
    def mode(self) -> str | None:
        """Return the current operating mode."""
        state = self.device_wrapper.get_state()
        if state is None:
            return None
        return state.get(ATTR_MODE)

    @property
    def is_on(self) -> bool:
        """Return True if the dehumidifier is on."""
        return self.device_wrapper.is_on

    @property
    def action(self) -> HumidifierAction | None:
        """Return the current action."""
        state = self.device_wrapper.get_state()
        if state is None:
            return None
        power = state.get(ATTR_POWER)
        if power == OFF_DRY_VALUE:
            return HumidifierAction.DRYING
        if power == ON_VALUE:
            return HumidifierAction.HUMIDIFYING
        return HumidifierAction.OFF

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        state = self.device_wrapper.get_state()
        if state is None:
            return None
        value = state.get(ATTR_CURRENT_HUMIDITY)
        return int(value) if value is not None else None

    @property
    def target_humidity(self) -> int | None:
        """Return the target humidity."""
        state = self.device_wrapper.get_state()
        if state is None:
            return None
        value = state.get(ATTR_TARGET_HUMIDITY)
        return int(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra state attributes."""
        attributes: dict[str, Any] = {}
        state = self.device_wrapper.get_state()

        if state is not None:
            # Expose all state keys except power (that is the entity state)
            attributes = {
                key: value for key, value in state.items() if key != ATTR_POWER
            }

        attributes[ATTR_LOCATION] = self.device_wrapper.device_stub.location_code
        attributes[ATTR_FILTER_REPLACEMENT_DATE] = (
            self.device_wrapper.device_stub.filter_replace_date
        )

        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the dehumidifier on."""
        await self.device_wrapper.async_turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the dehumidifier off."""
        await self.device_wrapper.async_turn_off()
        self.async_write_ha_state()

    async def async_set_humidity(self, humidity: int) -> None:
        """Set target humidity (35-70 %, 5 % steps)."""
        if not (
            DEHUMIDIFIER_MIN_HUMIDITY <= humidity <= DEHUMIDIFIER_MAX_HUMIDITY
            and humidity % DEHUMIDIFIER_HUMIDITY_STEP == 0
        ):
            LOGGER.warning(
                "Invalid humidity %d; must be %d-%d in steps of %d",
                humidity,
                DEHUMIDIFIER_MIN_HUMIDITY,
                DEHUMIDIFIER_MAX_HUMIDITY,
                DEHUMIDIFIER_HUMIDITY_STEP,
            )
            return

        await self.device_wrapper._driver.set_humidity(humidity)
        self.async_write_ha_state()

    async def async_set_mode(self, mode: str) -> None:
        """Set operating mode."""
        if mode not in DEHUMIDIFIER_MODES:
            LOGGER.warning("Unknown dehumidifier mode: %s", mode)
            return

        await self.device_wrapper._driver.set_mode(mode)
        self.async_write_ha_state()

    async def async_set_fan_speed(self, speed: str) -> None:
        """Set fan speed."""
        await self.device_wrapper._driver.set_fan_speed(speed)
        self.async_write_ha_state()
