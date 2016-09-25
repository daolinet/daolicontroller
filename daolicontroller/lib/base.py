"""Packet base class."""

import abc
import six

from oslo_config import cfg

CONF = cfg.CONF

LOCAL_PREFIX = "tap"

@six.add_metaclass(abc.ABCMeta)
class PacketBase(object):
    priority = 0

    def __init__(self, manager, ryuapp):
        self.manager = manager
        self.client = manager.client
        self.container = manager.container
        self.container.getc = self.getc
        self.ryuapp = ryuapp

    def getc(self, key):
        if not self.container.get(key):
            self.client.containers()
        return self.container.get(key)

    def gateway_get(self, dpid):
        return self.manager.gateway[dpid]

    @abc.abstractmethod
    def run(self, *args, **kwargs):
        """Run the packet service."""
        raise NotImplementedError()

    def port_get(self, dp, devname=None, id=None):
        if devname is None:
            devname = LOCAL_PREFIX + id[:11]

        if self.ryuapp.port_state.has_key(dp.id):
            return self.ryuapp.port_state[dp.id].get(devname)

    def _redirect(self, dp, inport, outport, **kwargs):
        ofp, ofp_parser, ofp_set, ofp_out = self.ofp_get(dp)

        timeout = kwargs.pop('timeout', 0)
        actions = [ofp_parser.OFPActionOutput(outport)]
        match = ofp_parser.OFPMatch(in_port=inport, **kwargs)

        self.add_flow(dp, match, actions, timeout=timeout)

    def ofp_get(self, dp):
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        ofp_set = ofp_parser.OFPActionSetField
        ofp_out = ofp_parser.OFPActionOutput
        return (ofp, ofp_parser, ofp_set, ofp_out)

    def packet_out(self, msg, dp, actions, in_port=None):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        if in_port is None:
            in_port = msg.match['in_port']

        out = parser.OFPPacketOut(
                datapath=dp, buffer_id=msg.buffer_id,
                in_port=in_port, actions=actions, data=data)

        dp.send_msg(out)

    def add_flow(self, dp, match=None, actions=None, timeout=None,
                 table_id=0, priority=None, inst=None):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        if timeout is None:
            timeout = 10

        if match is None:
            match = parser.OFPMatch()

        if inst is None:
            inst = [parser.OFPInstructionActions(
                    ofproto.OFPIT_APPLY_ACTIONS, actions)]

        mod = parser.OFPFlowMod(datapath=dp,
                                table_id=table_id,
                                command=ofproto.OFPFC_ADD,
                                idle_timeout=timeout,
                                priority=priority or self.priority,
                                match=match,
                                instructions=inst)
        dp.send_msg(mod)

    def delete_flow(self, dp, match, table_id=0):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        mod = parser.OFPFlowMod(datapath=dp,
                                table_id=table_id,
                                command=ofproto.OFPFC_DELETE,
                                out_port=ofproto.OFPP_ANY,
                                out_group=ofproto.OFPP_ANY,
                                match=match)
        dp.send_msg(mod)
