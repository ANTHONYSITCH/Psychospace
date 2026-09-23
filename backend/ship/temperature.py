class TemperatureSystem:
    """
    Système de température de l'habitat.
    """

    def __init__(self, temperature: float = 21.0):
        self.temperature = temperature

    def set_temperature(self, temperature: float):
        self.temperature = temperature

    def increase(self, amount: float):
        if amount < 0:
            raise ValueError("La variation ne peut pas être négative.")

        self.temperature += amount

    def decrease(self, amount: float):
        if amount < 0:
            raise ValueError("La variation ne peut pas être négative.")

        self.temperature -= amount

    def get_temperature(self) -> float:
        return round(self.temperature, 2)

    def get_status(self) -> dict:

        if self.temperature < 16 or self.temperature > 30:
            status = "critical"
        elif self.temperature < 18 or self.temperature > 27:
            status = "warning"
        else:
            status = "normal"

        return {
            "system": "temperature",
            "temperature_celsius": round(self.temperature, 2),
            "status": status
        }