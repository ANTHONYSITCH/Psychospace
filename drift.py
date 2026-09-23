class DriftEngine:

    def __init__(self, weights=None):

        self.weights = weights or {
            "sommeil_h": 0.25,
            "humeur": 0.20,
            "fatigue": 0.20,
            "activite": 0.15,
            "social": 0.20
        }

        self.anomaly_threshold = 1.5

    # ============================================================
    # Z-SCORE
    # ============================================================

    def calculate_z_score(self, value, mean, std):
        """
        Calcule l'écart normalisé par rapport à la baseline.
        """

        # Protection contre un écart-type nul ou trop faible.
        if std is None or std < 0.1:
            std = 0.1

        return (value - mean) / std

    # ============================================================
    # EVALUATION QUOTIDIENNE
    # ============================================================

    def evaluate_daily_signals(self, daily_data, baseline):
        """
        Calcule les z-scores et identifie les signaux préoccupants.
        """

        z_scores = {}
        concerning_signals = []

        for metric, stats in baseline.items():

            if metric not in daily_data:
                continue

            value = daily_data[metric]

            mean = stats["mean"]
            std = stats["std"]

            z = self.calculate_z_score(
                value,
                mean,
                std
            )

            # Une diminution est préoccupante pour ces métriques.
            if metric in [
                "sommeil_h",
                "humeur",
                "activite",
                "social"
            ]:
                risk_z = -z

            # Une augmentation est préoccupante pour la fatigue.
            elif metric == "fatigue":
                risk_z = z

            else:
                risk_z = abs(z)

            # On ne conserve que les écarts allant
            # dans le sens considéré comme préoccupant.
            risk_z = max(0, risk_z)

            z_scores[metric] = round(risk_z, 2)

            # Signal anormal
            if risk_z >= self.anomaly_threshold:

                concerning_signals.append({
                    "metric": metric,
                    "value": value,
                    "baseline_mean": mean,
                    "z_score": round(risk_z, 2)
                })

        return {
            "z_scores": z_scores,
            "concerning_signals": concerning_signals
        }

    # ============================================================
    # SCORE COMPOSITE
    # ============================================================

    def compute_composite_score(self, z_scores):
        """
        Calcule un score composite pondéré.
        """

        score = sum(
            self.weights.get(metric, 0.1)
            * z_scores.get(metric, 0)
            for metric in self.weights
        )

        return round(score, 2)

    # ============================================================
    # EVALUATION AVEC CONTEXTE DU VAISSEAU
    # ============================================================

    def evaluate_drift_with_context(
        self,
        history_z_scores,
        vessel_context=None
    ):
        """
        Détecte une dérive en tenant compte :

        - des signaux actuels
        - de leur persistance
        - du contexte du vaisseau

        Un incident important du vaisseau peut expliquer
        temporairement certaines variations.
        """

        # ========================================================
        # PAS DE DONNEES
        # ========================================================

        if not history_z_scores:

            return {
                "drift_detected": False,
                "reason": "Pas encore assez de données.",
                "confidence": "N/A",
                "signals": [],
                "consecutive_days": 0,
                "composite_score": 0
            }

        # ========================================================
        # INCIDENT TECHNIQUE DU VAISSEAU
        # ========================================================

        if (
            vessel_context is not None
            and vessel_context.has_major_incident()
        ):

            return {
                "drift_detected": False,
                "reason": (
                    "Incident technique du vaisseau en cours "
                    "— variation contextuelle."
                ),
                "confidence": "N/A",
                "signals": [],
                "consecutive_days": 0,
                "composite_score": 0,
                "contextual_event": True
            }

        # ========================================================
        # DONNEES DU DERNIER JOUR
        # ========================================================

        latest_day = history_z_scores[-1]

        current_z_scores = latest_day.get(
            "z_scores",
            {}
        )

        current_signals = latest_day.get(
            "concerning_signals",
            []
        )

        # Compatibilité avec un ancien format
        if not current_z_scores:

            current_z_scores = {
                metric: value
                for metric, value in latest_day.items()
                if isinstance(value, (int, float))
            }

        # Compatibilité avec un ancien format
        if not current_signals:

            current_signals = [
                {
                    "metric": metric,
                    "z_score": z
                }
                for metric, z in current_z_scores.items()
                if z >= self.anomaly_threshold
            ]

        # ========================================================
        # RECHERCHE DE LA PERSISTANCE
        # ========================================================

        consecutive_days = 0

        for day in reversed(history_z_scores):

            signals = day.get(
                "concerning_signals",
                []
            )

            if not signals:

                z_scores = day.get(
                    "z_scores",
                    {}
                )

                signals = [
                    z
                    for z in z_scores.values()
                    if z >= self.anomaly_threshold
                ]

            # Au moins 2 signaux anormaux ce jour-là
            if len(signals) >= 2:

                consecutive_days += 1

            else:

                break

        # ========================================================
        # SIGNAUX ACTUELS
        # ========================================================

        anomalous_metrics = [
            signal["metric"]
            for signal in current_signals
        ]

        nb_signals = len(anomalous_metrics)

        # ========================================================
        # SCORE COMPOSITE
        # ========================================================

        composite_score = self.compute_composite_score(
            current_z_scores
        )

        # ========================================================
        # DETECTION DE DERIVE
        # ========================================================

        # Une seule journée ne suffit pas.
        # Il faut au minimum :
        #
        # - 3 signaux anormaux
        # - pendant au moins 2 jours
        # - avec un score composite significatif

        drift_detected = (
            nb_signals >= 3
            and consecutive_days >= 2
            and composite_score >= 4.0
        )

        # ========================================================
        # NIVEAU DE CONFIANCE
        # ========================================================

        if nb_signals >= 4 and consecutive_days >= 3:

            confidence = "élevée"

        elif nb_signals >= 3 and consecutive_days >= 2:

            confidence = "moyenne"

        elif nb_signals >= 2:

            confidence = "faible"

        else:

            confidence = "faible"

        # ========================================================
        # STATUT
        # ========================================================

        if composite_score < 2:

            status = "normal"

        elif composite_score < 4:

            status = "surveillance"

        else:

            status = "alerte"

        # ========================================================
        # RAISON
        # ========================================================

        if drift_detected:

            reason = (
                f"{nb_signals} signaux dépassent le seuil "
                f"sur {consecutive_days} jours consécutifs."
            )

        elif status == "alerte":

            reason = (
                f"Signaux sévères détectés (score composite "
                f"{composite_score}), mais persistance pas encore "
                f"confirmée ({consecutive_days} jour(s) consécutif(s) "
                f"sur {2} requis)."
            )

        elif nb_signals >= 2:

            reason = (
                f"{nb_signals} signaux inhabituels détectés. "
                f"Surveillance recommandée."
            )

        else:

            reason = "Pas de dérive majeure détectée."

        return {
            "drift_detected": drift_detected,
            "reason": reason,
            "confidence": confidence,
            "signals": current_signals,
            "consecutive_days": consecutive_days,
            "composite_score": composite_score,
            "status": status,
        }