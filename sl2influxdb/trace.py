#!/usr/bin/env python

from calendar import timegm
from datetime import datetime
import logging
import queue
import sys

from obspy import UTCDateTime

from sl2influxdb.influx import InfluxDBExporter
from sl2influxdb.threads import q, shutdown_event, lock
from sl2influxdb.threads import last_packet_time


# default logger
logger = logging.getLogger('TraceInfluxDBExporter')


class TraceInfluxDBExporter(InfluxDBExporter):
    def __init__(self, host, port,
                 dbname, user, pwd,
                 flushtime,
                 dropdb=False,
                 geohash={}):
        super(TraceInfluxDBExporter, self).__init__(host, port,
                                                    dbname, user, pwd,
                                                    flushtime,
                                                    dropdb, geohash)
        logger.info('Flush time set to %d seconds' % self.flushtime)

    def make_stats(self, now):
        """ Build *queue* influxdb data point """
        t = timegm(now.utctimetuple()) * 1e9 \
            + now.microsecond * 1e3
        t_str = str(int(t))
        s = "queue,type=producer size=%d " % q.qsize() + t_str
        self.data.append(s)
        s = "queue,type=consumer size=%d " % len(self.data) + t_str
        self.data.append(s)

    def make_line_count(self, channel, starttime, delta, data):
        """ Build *seismogram* influxdb data point """
        cc = "count,channel=" + channel
        for i, v in enumerate(data):
            timestamp = starttime + i*delta
            t = timegm(timestamp.utctimetuple()) * 1e9 \
                + timestamp.microsecond * 1e3
            c = cc + " value=" + "%e " % v + str(int(t))
            self.data.append(c)

    def manage_data(self, trace):
        """ Build, pack and send waveform to influxdb

        - prepare trace's samples
        - send them to influxdb

        Return True is data have been pushed.
        """
        now = datetime.utcnow()
        delta = trace.stats['delta']
        starttime = trace.stats['starttime']
        endtime = trace.stats['endtime']
        channel = trace.get_id()

        # Update :
        # - timestamp of the last channel's packet received
        # - last sample time (endtime)
        lock.acquire()
        last_packet_time[channel] = {'timestamp': UTCDateTime(now),
                                     'endtime': endtime}
        lock.release()

        # Set all trace samples in the proper format.
        self.make_line_count(channel, starttime, delta, trace.data)

        # send data to influxdb if buffer is filled enough
        if len(self.data) > self.nb_data_max:
            now = datetime.utcnow()
            self.make_stats(now)
            logger.debug("Data sent")
            try:
                self.send_points(debug=False)
            except Exception as e:
                logger.critical(e)
                shutdown_event.set()
            else:
                return True
        else:
            return False

    def run(self):
        """ Run unless shutdown signal is received. """

        timeout = 0.1  # sec
        wait_time = 0  # sec

        while True:
            try:
                trace = q.get(timeout=timeout)
            except queue.Empty:
                # process queue before shutdown
                if q.empty() and shutdown_event.isSet():
                    logger.info("%s thread has caught *shutdown_event*" %
                                self.__class__.__name__)
                    sys.exit(0)

                wait_time += timeout
                if wait_time > self.flushtime:
                    if len(self.data) == 0:
                        # no data from seedlink thread
                        logger.info('Flush timer reached (%ds)' %
                                    self.flushtime
                                    + '. No data coming from seedlink thread!'
                                    + ' Network/connection down ?')
                    else:
                        # force data flush to influxdb
                        # even if data block is not completed
                        logger.info('Flush timer reached (%ds)' %
                                    self.flushtime
                                    + '. Force data flush to influxdb '
                                    + '(bsize=%d/%d)'
                                    % (len(self.data), self.nb_data_max))

                    now = datetime.utcnow()
                    self.make_stats(now)
                    try:
                        self.send_points()
                    except Exception as e:
                        logger.critical(e)
                        shutdown_event.set()
                        # self.force_shutdown(e)
                    wait_time = 0
            else:
                data_pushed = self.manage_data(trace)
                q.task_done()
                if data_pushed:
                    wait_time = 0
