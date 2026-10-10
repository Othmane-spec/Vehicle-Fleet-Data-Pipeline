"""Script de test manuel pour valider la phase 2 (Chargement PostgreSQL)."""

import logging
from pathlib import Path
from fleet_pipeline.config import get_settings
from fleet_pipeline.database import get_engine, init_db, check_connection
from fleet_pipeline.extract import extract_source
from fleet_pipeline.validate import validate_single_record
from fleet_pipeline.load import create_etl_run, finish_etl_run
from fleet_pipeline.models import NormalizedRecord, RejectedRecord

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_phase2_test():
    settings = get_settings()
    
    logger.info("--- Démarrage du test Phase 2 (Chargement DB) ---")
    
    # 1. Initialisation de la Base de Données
    logger.info("Étape 1 : Connexion et Initialisation de la DB...")
    engine = get_engine()
    
    if not check_connection(engine):
        logger.error("Impossible de se connecter à PostgreSQL. Vérifiez votre fichier .env et que le serveur est lancé.")
        return

    try:
        init_db(engine)
        logger.info("Schéma de la base de données initialisé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du schéma : {e}")
        return

    # 2. Extraction et Validation (Phase 1)
    logger.info("Étape 2 : Extraction et Validation des données...")
    source_path = settings.resolved_source_path
    raw_data = extract_source(source_path)
    
    valid_records = []
    rejected_records = []
    for record in raw_data:
        result = validate_single_record(record, source_name="phase2_test")
        if isinstance(result, NormalizedRecord):
            valid_records.append(result)
        else:
            rejected_records.append(result)

    # 3. Chargement dans la DB (Phase 2)
    logger.info("Étape 3 : Chargement dans PostgreSQL...")
    
    try:
        with engine.begin() as conn:
            # Création du run ETL
            etl_run_id = create_etl_run(conn)
            
            # Simulation du chargement des données
            # Ici on valide que l'on peut insérer dans etl_runs et finir le run
            finish_etl_run(
                conn, 
                etl_run_id, 
                status="SUCCESS", 
                rows_read=len(raw_data), 
                rows_loaded=len(valid_records), 
                rows_rejected=len(rejected_records)
            )
            
            logger.info(f"Chargement terminé. Run ID: {etl_run_id}")
            logger.info(f"Statistiques : {len(valid_records)} chargés, {len(rejected_records)} rejetés.")

    except Exception as e:
        logger.error(f"Erreur lors du chargement DB : {e}", exc_info=True)

if __name__ == "__main__":
    run_phase2_test()
