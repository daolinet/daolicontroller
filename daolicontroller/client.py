import logging

from docker import client
from docker import tls
from ryu import cfg

docker_opts = [
    cfg.BoolOpt('api_insecure',
                default=False,
                help='If set, ignore any SSL validation issues'),
    cfg.StrOpt('ca_file',
               help='Location of CA certificates file for '
                    'securing docker api requests (tlscacert).'),
    cfg.StrOpt('cert_file',
               help='Location of TLS certificate file for '
                    'securing docker api requests (tlscert).'),
    cfg.StrOpt('key_file',
               help='Location of TLS private key file for '
                    'securing docker api requests (tlskey).'),
]

CONF = cfg.CONF
CONF.register_opts(docker_opts, 'docker')

EXCLUDE = ['none', 'bridge', 'host']
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_DOCKER_API_VERSION = '1.19'

LOG = logging.getLogger(__name__)


class DockerHTTPClient(client.Client):
    def __init__(self, parent, url):
        self._parent = parent
        if (CONF.docker.cert_file or
                CONF.docker.key_file):
            client_cert = (CONF.docker.cert_file, CONF.docker.key_file)
        else:
            client_cert = None
        if (CONF.docker.ca_file or
                CONF.docker.api_insecure or
                client_cert):
            ssl_config = tls.TLSConfig(
                client_cert=client_cert,
                ca_cert=CONF.docker.ca_cert,
                verify=CONF.docker.api_insecure)
        else:
            ssl_config = False
        super(DockerHTTPClient, self).__init__(
            base_url=url,
            version=DEFAULT_DOCKER_API_VERSION,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            tls=ssl_config
        )

    def containers(self):
        res = self._result(self._get(self._url("/containers/json")), True)
        for r in res:
            if r['Id'] not in self._parent.container:
                if r['HostConfig']['NetworkMode'] not in EXCLUDE:
                    self.container(r['Id'])

    def container(self, cid):
        try:
            info = self.inspect_container(cid)
        except Exception as e:
            LOG.warn(e.message)
            return

        nodeIP = info.get('Node', {}).get('IP')
        networkName = info['HostConfig']['NetworkMode']
        net = info['NetworkSettings']['Networks'].get(networkName)
        if nodeIP and net:
            gateway = self._parent.gateway.get(nodeIP, {})
            c = {
                'Id': info['Id'],
                'Node': nodeIP,
                'NetworkName': networkName,
                'NetworkId': net['NetworkID'],
                'EndpointID': net['EndpointID'],
                'IPAddress': net['IPAddress'],
                'MacAddress': net['MacAddress'],
                'DataPath': gateway.get('DatapathID'),
                'VIPAddress': self._parent.ipam.alloc(),
            }
            return self._parent.container.new(c)

    def gateways(self):
        res = self._result(self._get(self._url("/api/gateways")), True)
        for r in res:
            self._parent.gateway.new(r)
        return res

    def gateway(self, dpid):
        url = self._url("/api/gateways/%s" % dpid)
        try:
            res = self._result(self._get(url), True)
            self._parent.gateway.new(res)
        except Exception as e:
            LOG.warn(e.message)
            res = None
        return res

    def policy(self, peer):
        url = self._url("/api/policy/%s" % peer)
        return self._result(self._get(url))

    def group(self, src, dst):
        res = self._result(self._get(self._url("/api/groups")), True)
        for r in res:
            url = self._url("/api/groups/" + r)
            members = self._result(self._get(url), True)
            if src in members and dst in members:
                return True
        return False

    def firewall(self, node, port):
        url = self._url("/api/firewalls/{0}/{1}".format(node, port))
        try:
            return self._result(self._get(url), True)
        except Exception:
            return None
