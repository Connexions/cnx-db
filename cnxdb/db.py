from sqlalchemy import MetaData

meta = MetaData()


class _Tables(object):

    metadata = None

    def __init__(self, metadata=meta):
        self.metadata = metadata

    def __getattr__(self, name):
        return self.metadata.tables[name]


tables = _Tables()
