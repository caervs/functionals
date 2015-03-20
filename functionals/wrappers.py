class OptionlessDecorator(object):
    def __init__(self, f):
        self.f = f

    @classmethod
    def decorate(cls, f):
        # TODO use partial to properly wrap
        return cls(f)
