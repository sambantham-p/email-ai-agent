import logging
from pathlib import Path
import sys

from utils.auth_util import initialize_authentication, initialize_gmail_authentication
from utils.config_util import load_config
from services.gmail_service import gmail_poll

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
main_logger = logging.getLogger("main")
main_logger.setLevel(logging.INFO)

config = load_config()


def main():
    main_logger.info("Starting the main function")
    main_logger.info("Calling auth file to get credentials")
    try:
        initialize_authentication()
        # initializing gmail service
        main_logger.info("Initializing gmail service")
        service = initialize_gmail_authentication()
        gmail_poll(
            service=service,
            gmail_config=config['gmail'],
            processing_config=config['processing']
        )
    except Exception as e:
        main_logger.error(e)
        sys.exit(1)




if __name__ == "__main__":
    main()
