import os
from nemoguardrails import RailsConfig, LLMRails
from src.core.config import get_settings

_rails_app = None

def get_rails():
    global _rails_app
    if _rails_app is None:
        settings = get_settings()
        os.environ["OPENAI_API_KEY"] = settings.LLM_API_KEY
        
        config_path = os.path.join(os.path.dirname(__file__), "config")
        config = RailsConfig.from_path(config_path)
        _rails_app = LLMRails(config)
    return _rails_app
