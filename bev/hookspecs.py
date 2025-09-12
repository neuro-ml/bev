import warnings


def hookimpl(func):
    warnings.warn('There are no more plugin hooks in bev')
    return func
