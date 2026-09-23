class VesselContext:
    """
    Représente l'état du vaisseau spatial.

    Ces données sont simulées pour le prototype PsychoSpace.
    Elles servent principalement à fournir du contexte
    au moteur de détection de dérive.
    """

    def __init__(
        self,
        oxygen_level=98.5,
        cabin_pressure=101.2,
        temperature=21.4,
        radiation_level=0.12,
        power_status="stable",
        communication_status="stable",
        alarm_active=False,
        incident_active=False,
        incident_type=None,
        incident_severity=0
    ):

        self.oxygen_level = oxygen_level
        self.cabin_pressure = cabin_pressure
        self.temperature = temperature
        self.radiation_level = radiation_level

        self.power_status = power_status
        self.communication_status = communication_status

        self.alarm_active = alarm_active

        self.incident_active = incident_active
        self.incident_type = incident_type
        self.incident_severity = incident_severity

    def has_major_incident(self):
        """
        Détermine si un incident important est actuellement actif.
        """

        return (
            self.incident_active
            and self.incident_severity >= 2
        )

    def get_context_dict(self):
        """
        Retourne les données sous forme de dictionnaire.
        """

        return {
            "oxygen_level": self.oxygen_level,
            "cabin_pressure": self.cabin_pressure,
            "temperature": self.temperature,
            "radiation_level": self.radiation_level,
            "power_status": self.power_status,
            "communication_status": self.communication_status,
            "alarm_active": self.alarm_active,
            "incident_active": self.incident_active,
            "incident_type": self.incident_type,
            "incident_severity": self.incident_severity
        }

    def get_context_string(self):
        """
        Produit une description lisible pour PsychoSpace/Ollama.
        """

        if self.incident_active:

            incident = (
                f"Incident en cours : {self.incident_type}. "
                f"Niveau de gravité : {self.incident_severity}/3."
            )

        else:

            incident = "Aucun incident majeur en cours."

        return (
            f"{incident}\n"
            f"Oxygène : {self.oxygen_level}%\n"
            f"Pression cabine : {self.cabin_pressure} kPa\n"
            f"Température : {self.temperature}°C\n"
            f"Radiation : {self.radiation_level}\n"
            f"Énergie : {self.power_status}\n"
            f"Communication : {self.communication_status}\n"
            f"Alarme active : {self.alarm_active}"
        )