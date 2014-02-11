import yaml


class _Conf(dict):

    _PATH = "/etc/battleships/system.yaml"
    
    def init(self):
        self._data = yaml.load(open(self._PATH))

    def __getitem__(self, key):
        return self._data[key]


Conf = _Conf()

