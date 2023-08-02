class UNetSingleton(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(type(cls), cls).__new__(cls)
            cls.__setup__(cls.instance)
        return cls.instance
    
    def __setup__(self):
        return
