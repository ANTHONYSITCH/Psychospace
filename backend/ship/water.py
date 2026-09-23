class WaterSystem:
    """
    Réservoir d'eau simulé.
    """

    def __init__(self, level: float = 100.0):
        self.level = max(0.0, min(100.0, level))

    def consume(self, amount: float) -> float:
        if amount < 0:
            raise ValueError("La consommation ne peut pas être négative.")

        self.level = max(0.0, self.level - amount)

        return self.level

    def recharge(self, amount: float) -> float:
        if amount < 0:
            raise ValueError("La recharge ne peut pas être négative.")

        self.level = min(100.0, self.level + amount)

        return self.level

    def get_level(self) -> float:
        return self.level

    def get_status(self) -> dict:

        if self.level <= 15:
            status = "critical"
        elif self.level <= 30:
            status = "warning"
        else:
            status = "normal"

        return {
            "system": "water",
            "level_percent": round(self.level, 2),
            "status": status
        }