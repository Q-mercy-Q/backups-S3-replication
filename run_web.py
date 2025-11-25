#!/usr/bin/env python3
"""
Web application entry point for S3 Backup Manager
"""

import os
import sys
import logging
import atexit
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.web.app import create_app_with_socketio
from app.services.scheduler_service import scheduler_service

def setup_logging():
    """Setup application logging"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"{log_dir}/web_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce verbosity for some loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)

def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting S3 Backup Manager Web Application...")
        
        # Create Flask app with SocketIO
        app, socketio = create_app_with_socketio()
        
        # Get host and port from environment or use defaults
        host = os.getenv('FLASK_HOST', '0.0.0.0')
        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
        
        logger.info(f"Starting web server on {host}:{port} (debug: {debug})")
        
        # Start the application
        if debug:
            # Development mode with auto-reload
            socketio.run(app, host=host, port=port, debug=debug, use_reloader=True)
        else:
            # Production mode
            socketio.run(app, host=host, port=port, debug=debug, use_reloader=False)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Failed to start web application: {e}")
        sys.exit(1)
    finally:
        # Ensure scheduler is stopped
        try:
            if scheduler_service.job_scheduler.running:
                scheduler_service.shutdown()
                logger.info("Scheduler service stopped during shutdown")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}")

if __name__ == '__main__':
    main()