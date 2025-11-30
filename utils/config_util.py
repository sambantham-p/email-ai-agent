import yaml
import sys
import logging

config_logger = logging.getLogger("config")


def load_config(path="config.yaml"):
    """Loads configuration from the YAML file."""
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        config_logger.error(f"Configuration file not found at: {path}")
        sys.exit(1)
    except Exception as e:
        config_logger.error(f"Error loading config.yaml: {e}")
        sys.exit(1)