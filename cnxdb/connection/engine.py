
__all__ = ('get_current_engine', 'set_current_engine',)


class _CurrentEngine(object):
    """A singleton used to hold the current engine instance."""

    _engine = None

    def get_engine(self):
        if self._engine is None:
            raise RuntimeError("Engine is not configured. "
                               "Try setting the current engine before "
                               "attempting to use it.")
        return self._engine

    def set_engine(self, value):
        self._engine = value


_engine = _CurrentEngine()
get_current_engine = _engine.get_engine
set_current_engine = _engine.set_engine
