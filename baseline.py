import numpy as np


class BaselineManager:
    def __init__(self, onboarding_days=7):
        self.onboarding_days = onboarding_days

    def calculate_initial_baseline(self, historical_data):
        """
        Calcule la baseline initiale à partir des données
        des premiers jours d'observation.
        """

        baseline = {}

        for metric, values in historical_data.items():

            if len(values) < self.onboarding_days:
                raise ValueError(
                    f"Pas assez de données pour l'onboarding "
                    f"({len(values)}/{self.onboarding_days} jours)."
                )

            mean = float(np.mean(values))
            std = float(np.std(values))

            # Évite un écart-type nul
            std = std if std > 0.01 else 0.5

            baseline[metric] = {
                "mean": round(mean, 2),
                "std": round(std, 2)
            }

        return baseline

    def update_baseline_moving_average(
        self,
        current_baseline,
        new_data,
        alpha=0.05
    ):
        """
        Met à jour progressivement la baseline.

        alpha faible = adaptation lente.
        """

        updated_baseline = {}

        for metric, stats in current_baseline.items():

            if metric in new_data:
                new_val = new_data[metric]

                new_mean = (
                    (1 - alpha) * stats["mean"]
                    + alpha * new_val
                )

                updated_baseline[metric] = {
                    "mean": round(float(new_mean), 2),
                    "std": stats["std"]
                }

            else:
                updated_baseline[metric] = stats

        return updated_baseline