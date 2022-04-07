class HashError(Exception):
    pass


class HashNotFound(HashError):
    pass


class InconsistentHash(HashError):
    pass


class RepositoryError(Exception):
    pass


class RepositoryNotFound(RepositoryError):
    pass


class InconsistentRepositories(RepositoryError):
    pass
