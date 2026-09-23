from backend.ship.ship_state import ship


def get_energy_level() -> dict:
    return ship.energy.get_status()


def get_oxygen_level() -> dict:
    return ship.oxygen.get_status()


def get_water_level() -> dict:
    return ship.water.get_status()


def get_temperature() -> dict:
    return ship.temperature.get_status()


def get_ship_status() -> dict:
    return ship.get_status()