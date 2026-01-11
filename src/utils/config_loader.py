import yaml
from utils.paths import CONFIG_DIR

class ConfigLoader:
    _config = None

    @classmethod
    def load(cls, env: str = "dev") -> dict:
        if cls._config is None:
            config_path = CONFIG_DIR / f"{env}.yaml"
            with open(config_path, "r", encoding="utf-8") as f:
                cls._config = yaml.safe_load(f)
        return cls._config
