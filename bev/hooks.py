import pluggy

from . import hookspecs
from .config import *

manager = pluggy.PluginManager('bev')
manager.add_hookspecs(hookspecs)
manager.load_setuptools_entrypoints('bev_plugin')
manager.hook.register_config_extensions()
