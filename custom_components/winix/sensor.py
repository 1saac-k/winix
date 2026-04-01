"""Winix sensor entities (air quality, filter life, humidity)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import WINIX_DOMAIN
from .const import (
    ATTR_AIR_AQI,
    ATTR_AIR_QUALITY,
    ATTR_AIR_QVALUE,
    ATTR_CURRENT_HUMIDITY,
    ATTR_FILTER_HOUR,
    ATTR_FILTER_REPLACEMENT_CYCLE,
    LOGGER,
    SENSOR_AIR_QVALUE,
    SENSOR_AQI,
    SENSOR_FILTER_LIFE,
    WINIX_DATA_COORDINATOR,
)
from .device_wrapper import WinixDeviceWrapper
from .manager import WinixEntity, WinixManager


def get_air_quality_attr(
    state: dict[str, str], wrapper: WinixDeviceWrapper
) -> dict[str, Any]:
    """Get air quality attribute."""

    attributes = {ATTR_AIR_QUALITY: None}
    if state is not None:
        attributes[ATTR_AIR_QUALITY] = state.get(ATTR_AIR_QUALITY)

    return attributes


def get_filter_replacement_cycle(
    state: dict[str, str], wrapper: WinixDeviceWrapper
) -> dict[str, Any]:
    """Get filter replacement cycle duration."""

    duration = wrapper.filter_alarm_duration  # in hours

    if duration:
        duration = f"{int(duration / (24 * 30))} months"

    return {ATTR_FILTER_REPLACEMENT_CYCLE: duration}


def get_filter_life(state: dict[str, str], wrapper: WinixDeviceWrapper) -> int | None:
    """Get filter life percentage."""

    return get_filter_life_percentage(
        state.get(ATTR_FILTER_HOUR), wrapper.filter_alarm_duration
    )


def get_filter_life_percentage(hours: str | None, total: int) -> int | None:
    """Get filter life percentage."""

    if hours is None:
        return None

    hours: int = int(hours)
    return int((total - hours) * 100 / total)


@dataclass(frozen=True, kw_only=True)
class WininxSensorEntityDescription(SensorEntityDescription):
    """Describe Winix sensor entity."""

    value_fn: Callable[[dict[str, str], WinixDeviceWrapper], StateType]
    extra_state_attributes_fn: Callable[[dict[str, str]], dict[str, Any]] | None = None
    exists_fn: Callable[[WinixDeviceWrapper], bool] = field(
        default=lambda _: True
    )


SENSOR_DESCRIPTIONS: tuple[WininxSensorEntityDescription, ...] = (
    # --- Air purifier sensors ---
    WininxSensorEntityDescription(
        key=SENSOR_AIR_QVALUE,
        icon="mdi:cloud",
        name="Air QValue",
        native_unit_of_measurement="qv",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state, wrapper: state.get(ATTR_AIR_QVALUE),
        extra_state_attributes_fn=get_air_quality_attr,
        exists_fn=lambda device: device.is_air_purifier,
    ),
    WininxSensorEntityDescription(
        key=SENSOR_FILTER_LIFE,
        icon="mdi:air-filter",
        name="Filter Life",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=get_filter_life,
        extra_state_attributes_fn=get_filter_replacement_cycle,
        exists_fn=lambda device: device.is_air_purifier,
    ),
    WininxSensorEntityDescription(
        key=SENSOR_AQI,
        icon="mdi:blur",
        name="AQI",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state, wrapper: state.get(ATTR_AIR_AQI),
        exists_fn=lambda device: device.is_air_purifier,
    ),
    # --- Dehumidifier sensors ---
    WininxSensorEntityDescription(
        key="current_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        name="Current Humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state, wrapper: state.get(ATTR_CURRENT_HUMIDITY),
        exists_fn=lambda device: device.is_dehumidifier,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Winix sensors."""
    data = hass.data[WINIX_DOMAIN][entry.entry_id]
    manager: WinixManager = data[WINIX_DATA_COORDINATOR]

    entities = [
        WinixSensor(wrapper, manager, description)
        for description in SENSOR_DESCRIPTIONS
        for wrapper in manager.get_device_wrappers()
        if description.exists_fn(wrapper)
    ]
    async_add_entities(entities)
    LOGGER.info("Added %s sensors", len(entities))


class WinixSensor(WinixEntity, SensorEntity):
    """Representation of a Winix Purifier sensor."""

    entity_description: WininxSensorEntityDescription

    def __init__(
        self,
        wrapper: WinixDeviceWrapper,
        coordinator: WinixManager,
        description: WininxSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(wrapper, coordinator)
        self.entity_description = description

        self._attr_unique_id = (
            f"{SENSOR_DOMAIN}.{WINIX_DOMAIN}_{description.key.lower()}_{self._mac}"
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes."""

        if self.entity_description.extra_state_attributes_fn is None:
            return None

        state = self.device_wrapper.get_state()
        return (
            None
            if state is None
            else self.entity_description.extra_state_attributes_fn(
                state, self.device_wrapper
            )
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        state = self.device_wrapper.get_state()
        return (
            None
            if state is None
            else self.entity_description.value_fn(state, self.device_wrapper)
        )
