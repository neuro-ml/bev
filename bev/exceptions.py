class BevError(Exception):
    pass


class HashError(BevError):
    pass


class HashNotFound(HashError):
    pass


class InconsistentHash(HashError):
    pass


class RepositoryError(BevError):
    pass


class RepositoryNotFound(RepositoryError):
    pass


class NameConflict(RepositoryError):
    pass


class InconsistentRepositories(RepositoryError):
    pass


class ConfigError(BevError):
    pass
