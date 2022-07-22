import pluggy

hookspec = pluggy.HookspecMarker('bev')
hookimpl = pluggy.HookimplMarker('bev')


@hookspec
def register_config_extensions():
    """
    Adds new config extensions to the registry.
    Typically, it is enough to trigger the importing of modules
    where your classes are defined and decorated with `register`.
    """
