from baseline import BaselineManager
from drift import DriftEngine
from memory import AstronautMemory
from ollama_client import PsychoSpaceLLM
from vessel_context import VesselContext


def run_demo_simulation():

    print("=== INITIALISATION DE LA DEMO PSYCHOSPACE ===")
    print()

    # ============================================================
    # 1. ONBOARDING : 7 PREMIERS JOURS
    # ============================================================

    onboarding_data = {
        "sommeil_h": [7.5, 7.2, 7.8, 7.4, 7.1, 7.6, 7.3],
        "humeur": [8, 7, 8, 7, 8, 7, 8],
        "fatigue": [2, 3, 2, 3, 2, 2, 3],
        "activite": [8, 7, 9, 8, 8, 7, 8],
        "social": [7, 8, 7, 8, 7, 7, 8]
    }

    baseline_mgr = BaselineManager()

    baseline = baseline_mgr.calculate_initial_baseline(
        onboarding_data
    )

    print("1. BASELINE CALCULEE")
    print(baseline)
    print()

    # ============================================================
    # 2. INITIALISATION DES MODULES
    # ============================================================

    drift_engine = DriftEngine()
    memory_mgr = AstronautMemory()
    llm_client = PsychoSpaceLLM()

    # Historique des journées réellement observées
    # dans le cadre de la détection de dérive.
    history_z = []

    # ============================================================
    # 3. JOUR 8 : INCIDENT TECHNIQUE DU VAISSEAU
    # ============================================================

    print("--- JOUR 8 : INCIDENT TECHNIQUE ---")

    day_8_data = {
        "sommeil_h": 4.5,
        "humeur": 4,
        "fatigue": 7,
        "activite": 9,
        "social": 5
    }

    # ------------------------------------------------------------
    # Contexte du vaisseau pendant l'incident
    # ------------------------------------------------------------

    vessel_context = VesselContext(
        oxygen_level=94.2,
        cabin_pressure=99.8,
        temperature=22.1,
        radiation_level=0.18,
        power_status="stable",
        communication_status="degraded",
        alarm_active=True,
        incident_active=True,
        incident_type="Anomalie du système de communication",
        incident_severity=2
    )

    z_8 = drift_engine.evaluate_daily_signals(
        day_8_data,
        baseline
    )

    # IMPORTANT :
    # Le jour 8 n'est PAS ajouté à history_z.
    #
    # Pourquoi ?
    # Parce que les variations observées pendant l'incident
    # sont contextualisées par l'événement technique.
    #
    # Elles ne doivent donc pas compter comme un jour
    # de dérive comportementale persistante.

    drift_res_8 = drift_engine.evaluate_drift_with_context(
        [],
        vessel_context=vessel_context
    )

    print(f"Statut : {drift_res_8['reason']}")
    print("Résultat : aucune dérive attribuée.")
    print()

    print("Contexte du vaisseau :")
    print(vessel_context.get_context_string())
    print()

    # ============================================================
    # 4. FIN DE L'INCIDENT
    # ============================================================

    vessel_context = VesselContext(
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
    )

    print("--- INCIDENT TERMINE ---")
    print("Le contexte du vaisseau est revenu à la normale.")
    print()

    # ============================================================
    # 5. JOURS 9 A 11 : DEGRADATION PROGRESSIVE
    # ============================================================

    simulated_days = [

        # --------------------------------------------------------
        # JOUR 9
        # --------------------------------------------------------

        {
            "sommeil_h": 5.2,
            "humeur": 5,
            "fatigue": 6,
            "activite": 5,
            "social": 4
        },

        # --------------------------------------------------------
        # JOUR 10
        # --------------------------------------------------------

        {
            "sommeil_h": 4.8,
            "humeur": 4,
            "fatigue": 7,
            "activite": 4,
            "social": 3
        },

        # --------------------------------------------------------
        # JOUR 11
        # --------------------------------------------------------

        {
            "sommeil_h": 4.5,
            "humeur": 3,
            "fatigue": 8,
            "activite": 3,
            "social": 2
        }
    ]

    print("--- JOURS 9 A 11 : DEGRADATION PROGRESSIVE ---")

    # ============================================================
    # 6. ANALYSE JOUR PAR JOUR
    # ============================================================

    for idx, day_data in enumerate(simulated_days, start=9):

        # --------------------------------------------------------
        # Calcul des signaux
        # --------------------------------------------------------

        z_day = drift_engine.evaluate_daily_signals(
            day_data,
            baseline
        )

        # IMPORTANT :
        # Contrairement au jour 8, les jours 9-11 sont ajoutés
        # à l'historique car le contexte technique est terminé.

        history_z.append(z_day)

        # --------------------------------------------------------
        # Détection de dérive
        # --------------------------------------------------------

        drift_res = drift_engine.evaluate_drift_with_context(
            history_z,
            vessel_context=vessel_context
        )

        print(
            f"\nJour {idx} | "
            f"Confiance : {drift_res['confidence']} | "
            f"Dérive détectée : "
            f"{drift_res['drift_detected']}"
        )

        print(
            f"Jours consécutifs : "
            f"{drift_res.get('consecutive_days', 0)}"
        )

        # --------------------------------------------------------
        # Affichage des signaux détectés
        # --------------------------------------------------------

        if drift_res.get("signals"):

            print("Signaux détectés :")

            for signal in drift_res["signals"]:

                print(
                    f"  - {signal['metric']} : "
                    f"valeur={signal['value']} | "
                    f"baseline={signal['baseline_mean']} | "
                    f"z-score={signal['z_score']}"
                )

            print(
                f"Score composite : "
                f"{drift_res.get('composite_score', 0)}"
            )

        else:

            print("Aucun signal anormal significatif.")

        # --------------------------------------------------------
        # Informations sur le vaisseau
        # --------------------------------------------------------

        print(
            f"Vaisseau : "
            f"O2={vessel_context.oxygen_level}% | "
            f"Pression={vessel_context.cabin_pressure} kPa | "
            f"Énergie={vessel_context.power_status} | "
            f"Communication={vessel_context.communication_status}"
        )

        # --------------------------------------------------------
        # Déclenchement de PsychoSpace
        # --------------------------------------------------------

        if drift_res["drift_detected"]:

            print()
            print("🚨 DECLENCHEMENT DE PSYCHOSPACE 🚨")
            print()

            memory_context = memory_mgr.get_context_string(
                "ASTRO-01"
            )

            print("Génération de la réponse via Ollama...")

            response = llm_client.generate_response(
                "Sarah",
                day_data,
                drift_res,
                memory_context
            )

            print()
            print("--- MESSAGE PSYCHOSPACE ---")
            print(response)

        else:

            print()
            print("PsychoSpace : aucune intervention déclenchée.")
            print()


# ================================================================
# POINT D'ENTREE
# ================================================================

if __name__ == "__main__":
    run_demo_simulation()