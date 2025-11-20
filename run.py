#!/usr/bin/env python3
"""
Точка входа для CLI версии S3 Backup Manager
"""
import logging
from app.utils.logger import setup_logging
from app.services.scheduler_service import scheduler_service
from app.utils.config import validate_environment

def main():
    """Основная функция CLI"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=== S3 Backup Manager CLI Started ===")
        
        # Валидация окружения
        validate_environment()
        logger.info("Environment validation successful")
        
        # Запускаем планировщик
        scheduler_service.start()
        logger.info("Scheduler service started")
        
        print("\nS3 Backup Manager is running in CLI mode.")
        print("Press Ctrl+C to stop the application.\n")
        
        # Бесконечный цикл для CLI
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            scheduler_service.shutdown()
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())