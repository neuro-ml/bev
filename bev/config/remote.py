from .location import LocationConfig, NginxConfig, SCPConfig
from .registry import register


# TODO: legacy
RemoteConfig = LocationConfig
SCPRemote = SCPConfig
NginxRemote = NginxConfig
register('ssh', SCPRemote)
register('http', NginxRemote)
