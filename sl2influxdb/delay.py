#!/usr/bin/env python

import sys
from calendar import timegm
from datetime import datetime
from obspy import UTCDateTime
from threads import shutdown_event, lock
from threads import last_packet_time
from influx import InfluxDBExporter
import logging

# default logger
logger = logging.getLogger('DelayInfluxDBExporter')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class LatencyDelayInfluxDBExporter(InfluxDBExporter):
    def __init__(self, host, port,
                 dbname, user, pwd,
                 flushtime,
                 dropdb=False,
                 geohash={}):
        super(LatencyDelayInfluxDBExporter, self).__init__(host, port,
                                                           dbname, user, pwd,
                                                           flushtime,
                                                           dropdb, geohash)
        self.refresh_rate = 1.  # sec.

    def make_channel_latency_delay(self, channel, last_packet):
        """ Latency and Delay computation

        Latency is the elapsed time between the current time and
        the time of the last sample from the last received packet.

        Delay is the elapsed time between two consecutive packet.
        Delay value is computed at each self.refresh_rate seconds,
        if no new packet was received, delay time increase linearly.

        Warning : definition may differ from other implementation
        (http://www.seiscomp3.org/doc/jakarta/current/apps/scqc.html)
        """
        now = datetime.utcnow()
        delay = UTCDateTime(now) - last_packet['timestamp']
        latency = UTCDateTime(now) - last_packet['endtime']

        try:
            geohash_tag = ",geohash=%s" % self.geohash[channel]
        except:
            geohash_tag = ""

        t = timegm(now.utctimetuple()) * 1e9 \
            + now.microsecond * 1e3
        t_str = str(int(t))

        # delay
        s = "delay,channel=%s" % channel + \
            geohash_tag + \
            " value=%.2f " % delay + \
            "%s" % t_str
        self.data.append(s)

        # latency
        l = "latency,channel=" + channel + \
            geohash_tag + \
            " value=" + "%.1f " % latency + \
            str(int(t))
        self.data.append(l)

    def manage_data(self):
        """ Prepare data to be sent to influxdb. """
        for c in last_packet_time.keys():
            lock.acquire()
            self.make_channel_latency_delay(c, last_packet_time[c])
            lock.release()
        try:
            self.send_points()
        except BaseException as e:
            logger.critical(e)
            shutdown_event.set()
        return True

    def run(self):
        """ Main loop. """
        while True:
            self.manage_data()
            shutdown_event.wait(self.refresh_rate)
            if shutdown_event.isSet():
                logger.info("%s thread has catched *shutdown_event*" %
                            self.__class__.__name__)
                sys.exit(0)
