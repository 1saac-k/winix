"""Winix Binary Sensor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WINIX_DOMAIN
from .const import (
    BINARY_SENSOR_WATER_BUCKET,
    LOGGER,
    WINIX_DATA_COORDINATOR,
)
from .device_wrapper import WinixDeviceWrapper
from .manager import WinixEntity, WinixManager


@dataclass(frozen=True, kw_only=True)
class WinixBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a Winix binary sensor entity."""

    is_on: Callable[[WinixDeviceWrapper], bool]


BINARY_SENSOR_DESCRIPTIONS: tuple[WinixBinarySensorEntityDescription, ...] = (
    WinixBinarySensorEntityDescription(
        key=BINARY_SENSOR_WATER_BUCKET,
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:bucket-outline",
        name="Water Bucket Full",
        is_on=lambda device: not device.is_water_bucket_available,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Winix binary sensors."""
    data = hass.data[WINIX_DOMAIN][entry.entry_id]
    manager: WinixManager = data[WINIX_DATA_COORDINATOR]

    entities = [
        WinixBinarySensor(wrapper, manager, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
        for wrapper in manager.get_device_wrappers()
    ]
    async_add_entities(entities)
    LOGGER.info("Added %s binary sensors", len(entities))


class WinixBinarySensor(WinixEntity, BinarySensorEntity):
    """Representation of a Winix binary sensor."""

    entity_description: WinixBinarySensorEntityDescription

    def __init__(
        self,
        wrapper: WinixDeviceWrapper,
        coordinator: WinixManager,
        description: WinixBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(wrapper, coordinator)
        self.entity_description = description

        self._attr_unique_id = (
            f"{BINARY_SENSOR_DOMAIN}.{WINIX_DOMAIN}_{description.key.lower()}_{self._mac}"
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on(self.device_wrapper)
