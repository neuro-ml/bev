from .registry import register
from .location import LocationConfig, SCPConfig, NginxConfig

# TODO: legacy
RemoteConfig = LocationConfig
SCPRemote = SCPConfig
NginxRemote = NginxConfig
register('ssh', SCPRemote)
register('http', NginxRemote)
