try:
    from functools import cached_property
except ImportError:
    from functools import lru_cache


    def cached_property(func):
        return property(lru_cache(None)(func))
