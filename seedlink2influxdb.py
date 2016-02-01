#!/usr/bin/env python

import sys
from obspy.seedlink import EasySeedLinkClient 
from obspy import UTCDateTime
from influxdb import InfluxDBClient
from datetime import datetime
from lxml import etree
from StringIO import StringIO
import re
from optparse import OptionParser
import logging
import signal
from calendar import timegm


# default logger
logger = logging.getLogger('obspy.seedlink')
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class InfluxDBExporter(object):
    def __init__(self, host, port, dbname, user, pwd):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.pwd = pwd
        self.client = None
        # add one item by influxdb field
        self.counts = []
        self.latency = []
        #
        self.TIME_MAX = 2*60.*60.
        # nb of blocks before sending
        # no more than 5000 (cf. influxdb doc.)
        self.nb_block_max = 4000
        self.nb_block = 0
        self.client = InfluxDBClient(host=host, port=port, database=dbname)
        self.create_db()
        # retention_policy = '2hours_policy'
        # dbClient.create_retention_policy(retention_policy, 
        #                                  duration='2h', 
        #                                  replication=None, default=True)

    def drop_db(self, dbname=None):
        if not dbname:
            dbname = self.dbname
        logger.info("Drop %s database." % dbname)
        self.client.drop_database(dbname)

    def create_db(self, dbname=None):
        if not dbname:
            dbname = self.dbname
        logger.info("open/create %s database." % dbname)
        self.client.create_database(dbname, if_not_exists=True)
        self.client.switch_database(dbname)

    def make_line_latency(self, channel, starttime, latency_value):
        timestamp = starttime.datetime
        t = timegm(timestamp.utctimetuple()) * 1e9 \
            + timestamp.microsecond * 1e3
        l = "latency,channel=" + channel + " value=" + \
            "%.1f " % latency_value + str(int(t))
        self.latency.append(l)

    def make_line_count(self, channel, starttime, delta, data):
        cc = "count,channel=" + channel
        for i, v in enumerate(data):
            timestamp = starttime + i*delta
            t = timegm(timestamp.utctimetuple()) * 1e9 \
                + timestamp.microsecond * 1e3
            c = cc + " value=" + "%.2f " % v + str(int(t))
            self.counts.append(c)

    def send_points(self):
        """Send points to influxsb

        to speed-up things make our own "data line"
        (bypass influxdb write_points python api)
        """
        data = '\n'.join(self.latency + self.counts)
        headers = self.client._headers
        headers['Content-type'] = 'application/octet-stream'
        self.client.request(
            url="write",
            method='POST',
            params={'db': self.client._database},
            data=data,
            expected_response_code=204,
            headers=headers
        )

        self.nb_block = 0
        self.counts = []
        self.latency = []
        return True

    def debug(self, channel):
        logger.debug("nb blocks = %d" % self.nb_block)
        logger.debug("*counts* size = %d" % len(self.counts))
        logger.debug("*latency* size = %d" % len(self.latency))


class EasySeedLinkClientException(Exception):
    """
    A base exception for all errors triggered explicitly by EasySeedLinkClient.
    """
    pass


class MySeedlinkClient(EasySeedLinkClient):
    def __init__(self, server, db):
        EasySeedLinkClient.__init__(self, server)
        self.influxdb = db
        self.stream_xml = self.get_info('STREAMS')
        self.selected_streams = []
        signal.signal(signal.SIGINT, self.kill_handler)

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

    def select_stream_re(self, pattern_net, pattern_sta, 
                         pattern_chan, pattern_loc=''):
        """Select stream based on regular expression"""
        info = self.get_stream_info()
        net_re = re.compile(pattern_net)
        sta_re = re.compile(pattern_sta)
        chan_re = re.compile(pattern_chan)
        loc_re = re.compile(pattern_loc)
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
        delta = trace.stats['delta']
        starttime = trace.stats['starttime']
        channel = trace.getId()
        now = datetime.utcnow()
        nbsamples = len(trace.data)

        if channel not in self.selected_streams:
            # print "Found not selected channel %s !" % channel
            return

        l = UTCDateTime(now) - (starttime + delta * (nbsamples - 1))

        # do not process 'old' data
        # if l > self.influxdb.TIME_MAX:
        #     return

        self.influxdb.make_line_count(
                channel,
                starttime,
                delta,
                trace.data)
        self.influxdb.nb_block += len(trace.data)

        self.influxdb.make_line_latency(channel,
                                        starttime + delta * (nbsamples - 1),
                                        l)
        self.influxdb.nb_block += 1

        # send data to influxdb if buffer is filled enough
        if self.influxdb.nb_block < self.influxdb.nb_block_max:
            self.influxdb.send_points()

    def on_seedlink_error(self):
        logger.error("[%s] seedlink error." % datetime.utcnow())

    def kill_handler(self, signal, frame):
        logger.info("kill signal catched !")
        client.conn.statefile = 'statefile.txt'
        self.conn.saveState('statefile.txt')
        self.conn.close()
        sys.exit(0)


if __name__ == '__main__':
    # Parse cmd line
    parser = OptionParser()
    parser.add_option("--dbserver", action="store", dest="dbserver",
                      default=None, help="InfluxDB server name")
    parser.add_option("--dbport", action="store", dest="dbport",
                      default='8083', help="db server port")
    parser.add_option("--slserver", action="store", dest="slserver",
                      default='renass-fw.u-strasbg.fr', 
                      help="seedlink server name")
    parser.add_option("--slport", action="store", dest="slport",
                      default='18000', help="seedlink server port")
    parser.add_option("--db", action="store", dest="dbname",
                      default='RT', help="influxdb name to use")
    parser.add_option("--dropdb",  action="store_true",
                      dest="dropdb", default=False,
                      help="[WARNING] drop previous database !")
    parser.add_option("--recover",  action="store_true",
                      dest="recover", default=False,
                      help="try to get stream from last run")
    (options, args) = parser.parse_args()

    # Connect to influxdb
    db = InfluxDBExporter(options.dbserver, options.dbport,
                          dbname=options.dbname,
                          user='seedlink', pwd='seedlink')

    if options.dropdb:
        db.drop_db()
        db.create_db()

    # Connect to a SeedLink server
    seedlink_url = ':'.join([options.slserver, options.slport])
    client = MySeedlinkClient(seedlink_url, db)

    # Select a stream and start receiving data
    # use regexp
    client.select_stream_re('FR', '.*', '(HHZ|EHZ)', '00')
    client.select_stream_re('FR', '.*', 'SHZ', '')
    client.select_stream_re('RD', '.*', 'BHZ', '.*')
    client.select_stream_re('(SZ|RT|IG)', '.*', '.*Z', '.*')

    if options.recover:
        client.conn.statefile = 'statefile.txt'
        client.conn.recoverState('statefile.txt')

        # prevent statefile to be overwitten each time a new packet 
        # arrives (take too much ressources)
        client.conn.statefile = None

    client.run()

