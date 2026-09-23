class EnergySystem:
    """
    Système énergétique simulé du vaisseau.

    Le niveau est exprimé en pourcentage.
    """

    def __init__(self, level: float = 100.0):
        self.level = max(0.0, min(100.0, level))

    def consume(self, amount: float) -> float:
        """
        Consomme de l'énergie.
        Retourne le nouveau niveau.
        """

        if amount < 0:
            raise ValueError("La consommation ne peut pas être négative.")

        self.level = max(0.0, self.level - amount)

        return self.level

    def recharge(self, amount: float) -> float:
        """
        Recharge le système énergétique.
        Retourne le nouveau niveau.
        """

        if amount < 0:
            raise ValueError("La recharge ne peut pas être négative.")

        self.level = min(100.0, self.level + amount)

        return self.level

    def get_level(self) -> float:
        """Retourne le niveau énergétique actuel."""
        return self.level

    def get_status(self) -> dict:
        """Retourne l'état complet du système."""

        if self.level <= 20:
            status = "critical"
        elif self.level <= 40:
            status = "warning"
        else:
            status = "normal"

        return {
            "system": "energy",
            "level_percent": round(self.level, 2),
            "status": status
        }