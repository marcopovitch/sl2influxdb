#!/usr/bin/env python

import sys
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError
from calendar import timegm
import logging
from datetime import datetime
from obspy import UTCDateTime
from threads import q, shutdown_event, last_packet_time, lock
import Queue

# default logger
logger = logging.getLogger('InfluxDBClient')
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class InfluxDBExporter(object):
    def __init__(self, host, port, dbname, user, pwd, dropdb=False):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.pwd = pwd
        self.client = None

        self.NB_MAX_TRY_REQUEST = 10  # nb of rqt error before aborting
        # self.TIME_MAX = 1*60.*60.

        # add one item by influxdb line
        self.data = []
        self.nb_data_max = 40000     # no more than 5000 (cf. influxdb doc.)

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

    def make_stats(self, now):
        t = timegm(now.utctimetuple()) * 1e9 \
            + now.microsecond * 1e3
        t_str = str(int(t))
        s = "queue,type=producer size=%d " % q.qsize() + t_str
        self.data.append(s)
        s = "queue,type=consumer size=%d " % len(self.data) + t_str
        self.data.append(s)

    def make_line_latency(self, channel, starttime, latency_value):
        timestamp = starttime.datetime
        t = timegm(timestamp.utctimetuple()) * 1e9 \
            + timestamp.microsecond * 1e3
        l = "latency,channel=" + channel + \
            " value=" + "%.1f " % latency_value + \
            str(int(t))
        self.data.append(l)

    def make_line_count(self, channel, starttime, delta, data):
        cc = "count,channel=" + channel
        for i, v in enumerate(data):
            timestamp = starttime + i*delta
            t = timegm(timestamp.utctimetuple()) * 1e9 \
                + timestamp.microsecond * 1e3
            c = cc + " value=" + "%.2f " % v + str(int(t))
            self.data.append(c)

    def send_points(self, debug=False):
        """Send points to influxsb

        to speed-up things make our own "data line"
        (bypass influxdb write_points python api)
        """
        data = '\n'.join(self.data[:self.nb_data_max])
        del self.data[:self.nb_data_max]

        headers = self.client._headers
        headers['Content-type'] = 'application/octet-stream'

        nb_try = 0
        while True:
            nb_try += 1
            try:
                self.client.request(url="write", 
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
                    logger.error("request failed: retrying (%d/%d)" % 
                                 (nb_try, self.NB_MAX_TRY_REQUEST))
                    continue

            break

    def manage_data(self, trace):
        delta = trace.stats['delta']
        starttime = trace.stats['starttime']
        channel = trace.getId()
        now = datetime.utcnow()
        nbsamples = len(trace.data)
        last_sample_time = starttime + delta * (nbsamples - 1)

        l = UTCDateTime(now) - last_sample_time

        lock.acquire()
        last_packet_time[channel] = last_sample_time
        lock.release()

        # do not process 'old' data
        # if l > self.TIME_MAX:
        #     return

        self.make_line_count(channel,
                             starttime,
                             delta,
                             trace.data)

        self.make_line_latency(channel,
                               starttime + delta * (nbsamples - 1),
                               l)

        # send data to influxdb if buffer is filled enough
        if len(self.data) > self.nb_data_max:
            now = datetime.utcnow()
            self.make_stats(now)
            logger.debug("Data sent")
            try:
                self.send_points(debug=False)
            except InfluxDBServerError as e:
                self.force_shutdown(e)

    def run(self):
        """Run unless shutdown signal is received.  """
        while True:
            try:
                self.manage_data(q.get(timeout=0.1))
            except Queue.Empty:
                # process queue before shutdown
                if q.empty() and shutdown_event.isSet():
                    logger.info("%s thread has catched *shutdown_event*" %
                                self.__class__.__name__)
                    sys.exit(0)
            else:
                q.task_done()


class DelayInfluxDBExporter(InfluxDBExporter):
    def __init__(self, host, port, dbname, user, pwd, dropdb=False):
        super(DelayInfluxDBExporter, self).__init__(host, port, 
                                                    dbname, user, pwd, 
                                                    dropdb)

    def make_line_channel_delay(self, channel, last_sample_time):
        now = datetime.utcnow()
        t = timegm(now.utctimetuple()) * 1e9 \
            + now.microsecond * 1e3
        t_str = str(int(t))
        delay = UTCDateTime(now) - UTCDateTime(last_sample_time)
        s = "delay,channel=%s " % channel + \
            "value=%.2f " % delay + \
            "%s" % t_str
        self.data.append(s)

    def make_line_delay(self):
        for c in last_packet_time.keys():
            lock.acquire()
            self.make_line_channel_delay(c, last_packet_time[c])
            lock.release()

    def manage_data(self):
        self.make_line_delay()
        try:
            self.send_points()
        except InfluxDBServerError as e:
            self.force_shutdown(e)

    def run(self):
        while True:
            self.manage_data()
            shutdown_event.wait(1.)
            if shutdown_event.isSet():
                logger.info("%s thread has catched *shutdown_event*" %
                            self.__class__.__name__)
                sys.exit(0)






