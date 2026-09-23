import requests


class PsychoSpaceLLM:

    def __init__(
        self,
        model="llama3.2:1b",
        url="http://localhost:11434/api/generate"
    ):
        self.model = model
        self.url = url

        
    def generate_response(
        self,
        name,
        daily_data,
        drift_result,
        memory_context
    ):
        """
        Génère une réponse PsychoSpace à partir des données
        quotidiennes, de la dérive détectée et de la mémoire.
        """

        signals = drift_result.get("signals", [])

        # --------------------------------------------------------
        # Construction des signaux observés
        # --------------------------------------------------------

        signal_text = ""

        for signal in signals:

            metric = signal.get("metric", "inconnu")
            value = signal.get("value", "N/A")
            baseline = signal.get("baseline_mean", "N/A")
            z_score = signal.get("z_score", "N/A")

            signal_text += (
                f"- {metric} : valeur={value}, "
                f"baseline={baseline}, "
                f"z-score={z_score}\n"
            )

        if not signal_text:
            signal_text = "Aucun signal préoccupant actuellement."

        # --------------------------------------------------------
        # Prompt système
        # --------------------------------------------------------

        system_prompt = """
Tu es PsychoSpace, un assistant de soutien pour une mission
spatiale longue durée.

Ton rôle est d'observer les variations comportementales,
émotionnelles et physiologiques déclarées par l'astronaute.

IMPORTANT :

1. Tu ne poses JAMAIS de diagnostic médical.

2. Tu ne dois jamais dire qu'une personne est :
   - dépressive
   - anxieuse
   - malade
   - en burn-out
   - psychologiquement instable

   uniquement à partir de données numériques.

3. Une valeur d'humeur basse ne constitue PAS un diagnostic.

4. Tu dois décrire les données comme des OBSERVATIONS.

Exemples :

MAUVAIS :
"Votre humeur indique une légère dépression."

BON :
"Votre humeur déclarée est actuellement de 5/10,
en dessous de votre niveau habituel."

MAUVAIS :
"Vous êtes anxieux."

BON :
"Les données montrent une variation inhabituelle
par rapport à votre baseline."

5. Tu dois comparer les données actuelles à la baseline
lorsque celle-ci est disponible.

6. Tu dois tenir compte du contexte et des événements récents.

7. Tu dois éviter de dramatiser.

8. Tu dois utiliser un ton calme, humain, rassurant
et professionnel.

9. Tu ne dois jamais inventer d'informations sur l'astronaute.

10. Si plusieurs signaux persistent pendant plusieurs jours,
tu peux indiquer qu'une tendance mérite une attention particulière.

11. Tu peux proposer des actions simples :
   - repos
   - sommeil
   - pause
   - activité légère
   - échange avec un membre de l'équipage
   - observation de l'évolution

12. Ne prescris jamais de médicament.

13. Ne transforme jamais une corrélation en certitude.

14. Si la situation semble importante ou persistante,
encourage l'astronaute à en parler à un membre humain
approprié de l'équipage ou au support médical de la mission.

STRUCTURE OBLIGATOIRE :

**Observation**

Décris uniquement ce que montrent les données.

**Vérification contextuelle**

Explique que les variations doivent être interprétées
dans leur contexte et indique les informations pertinentes
disponibles dans la mémoire.

**Proposition bienveillante**

Propose une ou deux actions simples et concrètes.

Ne pose pas de diagnostic.
"""

        # --------------------------------------------------------
        # Prompt utilisateur
        # --------------------------------------------------------

        user_prompt = f"""
Astronaute : {name}

DONNÉES DU JOUR :
{daily_data}

SIGNAUX DÉTECTÉS :
{signal_text}

DÉRIVE DÉTECTÉE :
{drift_result.get("drift_detected", False)}

NIVEAU DE CONFIANCE :
{drift_result.get("confidence", "N/A")}

SCORE COMPOSITE :
{drift_result.get("composite_score", "N/A")}

JOURS CONSÉCUTIFS :
{drift_result.get("consecutive_days", 0)}

RAISON :
{drift_result.get("reason", "N/A")}

CONTEXTE MÉMOIRE :
{memory_context}

Génère maintenant une réponse PsychoSpace en français.

Respecte strictement cette structure :

**Observation**

**Vérification contextuelle**

**Proposition bienveillante**

Ne pose aucun diagnostic médical.
"""

        # --------------------------------------------------------
        # Appel Ollama
        # --------------------------------------------------------

        payload = {
            "model": self.model,
            "prompt": system_prompt + "\n\n" + user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }

        try:

            response = requests.post(
                self.url,
                json=payload,
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            return data.get(
                "response",
                "Aucune réponse générée par PsychoSpace."
            ).strip()

        except requests.exceptions.RequestException as error:

            return (
                "PsychoSpace n'a pas pu contacter le modèle Ollama.\n"
                f"Erreur : {error}"
            )

        except Exception as error:

            return (
                "Une erreur est survenue lors de la génération "
                f"de la réponse : {error}"
            )
