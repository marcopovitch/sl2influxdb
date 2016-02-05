#!/usr/bin/env python

import sys
from obspy.seedlink import EasySeedLinkClient 
from datetime import datetime
from lxml import etree
from StringIO import StringIO
import re
import logging
from threads import q, shutdown_event

# default logger
logger = logging.getLogger('obspy.seedlink')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class EasySeedLinkClientException(Exception):
    """
    A base exception for all errors triggered explicitly by EasySeedLinkClient.
    """
    pass


class MySeedlinkClient(EasySeedLinkClient):
    def __init__(self, server, streams, statefile):
        EasySeedLinkClient.__init__(self, server)
        self.selected_streams = []
        # get from server avalaible streams
        self.stream_xml = self.get_info('STREAMS')
        # streams wanted by user
        for patterns in streams:
            self.select_stream_re(patterns)

        if statefile:
            self.conn.statefile = statefile
            # recover last packet indexes from previous run
            self.conn.recoverState(statefile)
            # prevent statefile to be overwitten each time a new packet
            # arrives (take too much ressources)
            self.conn.statefile = None

    def get_stream_info(self):
        """Parse xml stream info returned by server"""
        stream_info = []
        self.stream_xml = self.stream_xml.replace('encoding="utf-8"', '')
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(StringIO(self.stream_xml), parser)
        root = tree.getroot()
        for s in root.iterchildren():
            if s.tag == "station":
                s_dic = dict(zip(s.keys(), s.values()))
                s_dic['channel'] = []
                stream_info.append(s_dic)
                for c in s.iterchildren():
                    if c.tag == "stream":
                        c_dic = dict(zip(c.keys(), c.values()))
                        s_dic['channel'].append(c_dic)
        return stream_info

    def show_stream_info(self):
        """Show xml parsed stream info returned by server"""
        info = self.get_stream_info()
        for s in info:
            for c in s['channel']:
                print s['network'], s['name'],
                print c['location'], c['seedname'], s['stream_check']

    def select_stream_re(self, pattern):
        """Select stream based on regular expression"""
        net_re = re.compile(pattern[0])
        sta_re = re.compile(pattern[1])
        chan_re = re.compile(pattern[2])
        loc_re = re.compile(pattern[3])

        info = self.get_stream_info()  # avalaible streams from server
        for s in info:
            if not net_re.match(s['network']) or not sta_re.match(s['name']):
                continue
            for c in s['channel']:
                if chan_re.match(c['seedname']) \
                   and loc_re.match(c['location']):
                    self.add_stream(s['network'], s['name'], 
                                    c['seedname'], c['location'])

    def add_stream(self, net, sta, chan, loc):
        """Add stream to be proceseed 
           it is not possible to add location code here
        """
        self.select_stream(net, sta, chan)
        stream = ".".join([net, sta, loc, chan])
        self.selected_streams.append(stream)
        logger.info("stream %s added" % stream)

    def on_data(self, trace):
        """Implement the on_data callback"""
        channel = trace.getId()
        if channel not in self.selected_streams:
            return

        q.put(trace, block=True, timeout=None)

        if shutdown_event.isSet():
            logger.info("%s thread has catched *shutdown_event*" %
                        self.__class__.__name__)

            self.stop_seedlink()

    def on_seedlink_error(self):
        logger.error("[%s] seedlink error." % datetime.utcnow())

    def stop_seedlink(self):
        self.conn.statefile = 'statefile.txt'
        self.conn.saveState('statefile.txt')
        self.conn.close()
        sys.exit(0)
