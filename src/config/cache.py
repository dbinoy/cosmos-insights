redis_url = 'redis://localhost:6379/0'
#redis_url = 'redis://:M7J2wy3NOJYm7JdHQNDOmdTSCmRaXbWuOAzCaEensaE=:@dash-redis-cache.redis.cache.windows.net:6380/0'
cache_config = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': redis_url,
    'CACHE_DEFAULT_TIMEOUT': 86400
}
