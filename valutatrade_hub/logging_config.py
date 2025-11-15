import logging
from logging.handlers import RotatingFileHandler
import os

os.makedirs('valutatrade_hub/logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('valutatrade_hub/logs/actions.log'),
        logging.StreamHandler()  
    ]
)

handler = RotatingFileHandler('valutatrade_hub/logs/actions.log', maxBytes=5*1024*1024, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logging.getLogger().addHandler(handler)

logger = logging.getLogger(__name__)
