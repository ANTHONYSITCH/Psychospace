from backend.ship.energy import EnergySystem
from backend.ship.oxygen import OxygenSystem
from backend.ship.water import WaterSystem
from backend.ship.temperature import TemperatureSystem


class ShipState:

    def __init__(self):
        self.energy = EnergySystem(100)
        self.oxygen = OxygenSystem(100)
        self.water = WaterSystem(100)
        self.temperature = TemperatureSystem(21)

    def get_status(self) -> dict:
        return {
            "energy": self.energy.get_status(),
            "oxygen": self.oxygen.get_status(),
            "water": self.water.get_status(),
            "temperature": self.temperature.get_status()
        }


# Instance unique du vaisseau
ship = ShipState()