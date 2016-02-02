#!/usr/bin/env python

import sys
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError
from calendar import timegm
import logging
from datetime import datetime
from obspy import UTCDateTime
from threads import q

# default logger
logger = logging.getLogger('Influx')
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class InfluxDBExporter(object):
    def __init__(self, host, port, dbname, user, pwd, dropdb=False):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.pwd = pwd
        self.client = None

        self.NB_MAX_TRY_REQUEST = 300  # nb of rqt error before aborting
        self.TIME_MAX = 2*60.*60.    # nb of blocks before sending to db
        self.nb_block_max = 4000     # no more than 5000 (cf. influxdb doc.)

        # add one item by influxdb field
        self.counts = []
        self.latency = []
        self.nb_block = 0

        self.client = InfluxDBClient(host=host, port=port, database=dbname)
        if dropdb:
            self.drop_db()
        self.create_db()

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
        l = "latency,channel=" + channel + \
            " value=" + "%.1f," % latency_value + \
            "ts=" + "%s.%s " % (starttime.strftime('%s'),
                                starttime.microsecond) + \
            str(int(t))
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

        nb_try = 0
        while True:
            nb_try += 1
            try:
                self.client.request(
                    url="write",
                    method='POST',
                    params={'db': self.client._database},
                    data=data,
                    expected_response_code=204,
                    headers=headers
                )
            except InfluxDBServerError as e:
                if nb_try > self.NB_MAX_TRY_REQUEST:
                    raise e
                else:
                    print "request failed: retrying (%d/%d)" % \
                          (nb_try, self.NB_MAX_TRY_REQUEST)
                    continue
            break

        self.nb_block = 0
        self.counts = []
        self.latency = []
        return True

    def manage_trace(self, trace):
        delta = trace.stats['delta']
        starttime = trace.stats['starttime']
        channel = trace.getId()
        now = datetime.utcnow()
        nbsamples = len(trace.data)

        l = UTCDateTime(now) - (starttime + delta * (nbsamples - 1))

        # do not process 'old' data
        # if l > self.TIME_MAX:
        #     return

        self.make_line_count(
                channel,
                starttime,
                delta,
                trace.data)

        self.nb_block += len(trace.data)

        self.make_line_latency(channel,
                               starttime + delta * (nbsamples - 1),
                               l)
        self.nb_block += 1

        # send data to influxdb if buffer is filled enough
        if self.nb_block < self.nb_block_max:
            self.send_points()

    def debug(self, channel):
        logger.debug("nb blocks = %d" % self.nb_block)
        logger.debug("*counts* size = %d" % len(self.counts))
        logger.debug("*latency* size = %d" % len(self.latency))

    def run(self):
        while True:
            self.manage_trace(q.get(block=True, timeout=None))
        return


