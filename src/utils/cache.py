from flask_caching import Cache
from src.config.cache import cache_config

cache = Cache(config=cache_config)