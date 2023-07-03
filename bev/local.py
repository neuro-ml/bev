class LocalVersion:
    """A class used to denote the current uncommitted version of data"""

    @classmethod
    def __getversion__(cls):
        raise RuntimeError("The `Local` object doesn't have a well-defined version")

    def __eq__(self, other):
        return isinstance(other, LocalVersion)


Local = LocalVersion()
