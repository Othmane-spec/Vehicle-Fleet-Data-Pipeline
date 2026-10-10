"""Script de test manuel pour valider l'étape 1 du pipeline (Extraction -> Normalisation -> Validation)."""

import logging

from fleet_pipeline.config import get_settings
from fleet_pipeline.extract import extract_source
from fleet_pipeline.models import NormalizedRecord
from fleet_pipeline.validate import validate_single_record

# Configuration des logs pour voir ce qui se passe
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_manual_test():
    settings = get_settings()
    source_path = settings.resolved_source_path

    logger.info("--- Démarrage du test manuel ---")
    logger.info(f"Source : {source_path}")

    try:
        # 1. Extraction
        logger.info("Étape 1 : Extraction des données...")
        raw_data = extract_source(source_path)
        logger.info(f"Extraction réussie : {len(raw_data)} enregistrements trouvés.")

        # 2. Validation & Normalisation
        logger.info("Étape 2 : Validation et Normalisation...")
        valid_records = []
        rejected_records = []

        for i, record in enumerate(raw_data):
            result = validate_single_record(record, source_name="manual_test")

            if isinstance(result, NormalizedRecord):
                valid_records.append(result)
            else:
                rejected_records.append(result)

        # 3. Affichage des résultats
        logger.info("\n--- RÉSULTATS DU TEST ---")
        logger.info(f"Total traité    : {len(raw_data)}")
        logger.info(f"Valides ✅       : {len(valid_records)}")
        logger.info(f"Rejetés ❌       : {len(rejected_records)}")

        if valid_records:
            logger.info("\nExemple d'enregistrement valide :")
            logger.info(valid_records[0].model_dump_json(indent=2))

        if rejected_records:
            logger.info("\nExemple d'enregistrement rejeté :")
            logger.info(rejected_records[0].model_dump_json(indent=2))

    except Exception as e:
        logger.error(f"Erreur lors du test : {e}", exc_info=True)


if __name__ == "__main__":
    run_manual_test()
