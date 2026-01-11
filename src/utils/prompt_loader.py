from utils.paths import PROMPTS_DIR

class PromptLoader:
    _cache: dict[str, str] = {}

    @classmethod
    def load(cls, prompt_name: str) -> str:
        if prompt_name not in cls._cache:
            prompt_path = PROMPTS_DIR / prompt_name
            cls._cache[prompt_name] = prompt_path.read_text(encoding="utf-8")
        return cls._cache[prompt_name]
