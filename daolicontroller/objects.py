from netaddr import IPNetwork


class Container(dict):
    def new(self, container):
        # Dont cache container if not ip address,
        # so dont support multi-tenant yet in this version.
        if container['MacAddress'] and container['IPAddress']:
            for key in ('Id', 'EndpointID', 'MacAddress', 'IPAddress'):
                self[container[key]] = container

    def remove(self, id):
        container = self.get(id)
        if container:
            for key in ('Id', 'EndpointID', 'MacAddress', 'IPAddress'):
                del self[container[key]]


class PortState(dict):
    def __init__(self):
        super(PortState, self).__init__()

    def add(self, port):
        self[port.port_no] = self[port.name] = port

    def remove(self, port):
        if self.has_key(port.port_no):
            del self[port.port_no]
        if self.has_key(port.name):
            del self[port.name]


class Gateway(dict):
    def new(self, gateway):
        self[gateway['Node']] = gateway
        self[gateway['DatapathID']] = gateway


class HashPort:
    def __init__(self):
        self._ports = {}

    def keys(self):
        return self._ports.keys()

    def has_key(self, key):
        return self._ports.has_key(key)

    def get(self, key):
        return self._ports.get(key)

    def set(self, key, value):
        self._ports[key] = value

    def update(self, key, value):
        self.set(key, value)

    def remove(self, key):
        try:
            del self._ports[key]
        except KeyError:
            pass

    def clear(self):
        self._ports.clear()

    def __len__(self):
        return len(self._ports)
