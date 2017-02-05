#!/usr/bin/env python

import sys
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError, \
                                InfluxDBClientError
import requests.exceptions
from calendar import timegm
import logging
from datetime import datetime
from obspy import UTCDateTime
from threads import q, shutdown_event, lock
from threads import last_packet_time
import Queue

# default logger
logger = logging.getLogger('InfluxDBClient')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class InfluxDBExporter(object):
    def __init__(self, host, port,
                 dbname, user, pwd,
                 db_management, geohash={}):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.pwd = pwd
        self.client = None
        self.geohash = geohash

        # nb of rqt error before aborting
        self.NB_MAX_TRY_REQUEST = 10
        # holds 'point' to be send to influxdb (1 by line)
        self.data = []
        # max batch size to send:  no more than 5000 (cf. influxdb doc.)
        self.nb_data_max = 5000

        self.client = InfluxDBClient(host=host, port=port, database=dbname)

        if db_management:
            self.prepare_db(db_management)

    def prepare_db(self, db_management):
        if db_management['drop_db']:
            self.drop_db()
        self.create_db()
        self.set_retention_policies(db_management['retention'])

    def drop_db(self, dbname=None):
        if not dbname:
            dbname = self.dbname
        logger.info("Drop %s database." % dbname)
        try:
            self.client.drop_database(dbname)
        except:
            logger.info("Can't drop %s database (not existing yet ?)."
                        % dbname)

    def create_db(self, dbname=None):
        if not dbname:
            dbname = self.dbname
        logger.info("Open/Create %s database." % dbname)
        # self.client.create_database(dbname, if_not_exists=True)
        self.client.create_database(dbname)
        self.client.switch_database(dbname)

    def set_retention_policies(self, days, dbname=None):
        if not dbname:
            dbname = self.dbname
        name = "in_days"
        logger.info("Setting %s retention policy on %s database, keep=%d days."
                    % (name, dbname, days))
        try:
            self.client.create_retention_policy(name,
                                                duration="%dd" % days,
                                                replication="1",
                                                database=dbname, default=True)
        except:
            self.client.alter_retention_policy(name,
                                               database=dbname,
                                               duration="%dd" % days,
                                               replication=1,
                                               default=True)

    def make_stats(self, now):
        """ Build *queue* influxdb data point """
        t = timegm(now.utctimetuple()) * 1e9 \
            + now.microsecond * 1e3
        t_str = str(int(t))
        s = "queue,type=producer size=%d " % q.qsize() + t_str
        self.data.append(s)
        s = "queue,type=consumer size=%d " % len(self.data) + t_str
        self.data.append(s)

    def make_line_latency(self, channel, starttime, latency_value):
        """ Build *latency* influxdb data point """
        timestamp = starttime.datetime
        t = timegm(timestamp.utctimetuple()) * 1e9 \
            + timestamp.microsecond * 1e3
        try:
            geohash_tag = ",geohash=%s" % self.geohash[channel]
        except:
            geohash_tag = ""

        l = "latency,channel=" + channel + \
            geohash_tag + \
            " value=" + "%.1f " % latency_value + \
            str(int(t))
        self.data.append(l)

    def make_line_count(self, channel, starttime, delta, data):
        """ Build *seimogram* influxdb data point """
        cc = "count,channel=" + channel
        for i, v in enumerate(data):
            timestamp = starttime + i*delta
            t = timegm(timestamp.utctimetuple()) * 1e9 \
                + timestamp.microsecond * 1e3
            c = cc + " value=" + "%.2f " % v + str(int(t))
            self.data.append(c)

    def send_points(self, debug=False):
        """ Send all data points to influxdb

        To speed-up things make our own "data line"
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
            except (InfluxDBServerError,
                    InfluxDBClientError,
                    requests.exceptions.ConnectionError) as e:
                if nb_try > self.NB_MAX_TRY_REQUEST:
                    raise e
                else:
                    logger.error("Request failed (%s)" % e)
                    logger.error("retrying (%d/%d)" %
                                 (nb_try, self.NB_MAX_TRY_REQUEST))
                    continue
            break

    def manage_data(self, trace):
        """ Build/pack data and send them to influxdb

        - prepare :
            - trace's samples
            - latency/delay :
                Note that definition may differ !
                - latency (http://ds.iris.edu/ds/nodes/dmc/data/latency/)
                - delay (http://www.seiscomp3.org/doc/jakarta/current/apps/scqc.html)
                Here latency is the time between the time of last sample of a given block 
                and when this block arrives into the datacenter.
                Delay is the time between to consecutive block (ie. kind of transit time)
        - send them to influxdb

        Return True is data have been pushed.
        """
        now = datetime.utcnow()
        delta = trace.stats['delta']
        starttime = trace.stats['starttime']
        endtime = trace.stats['endtime']
        channel = trace.get_id()

        # Update timestamp of the last and previous channel's packet received
        lock.acquire()
        try:
            previous_ptime = last_packet_time[channel]['last']
        except:
            previous_ptime = None
        last_ptime = UTCDateTime(now)
        last_packet_time[channel] = {'previous': previous_ptime,
                                     'last': last_ptime}
        lock.release()

        # Set all trace samples in the proper format.
        self.make_line_count(channel, starttime, delta, trace.data)

        # Latency
        latency = UTCDateTime(now) - endtime
        self.make_line_latency(channel, endtime, latency)

        # send data to influxdb if buffer is filled enough
        if len(self.data) > self.nb_data_max:
            now = datetime.utcnow()
            self.make_stats(now)
            logger.debug("Data sent")
            try:
                self.send_points(debug=False)
            except InfluxDBServerError as e:
                self.force_shutdown(e)
            else:
                return True
        else:
            return False

    def run(self):
        """
        Run unless shutdown signal is received.
        """

        # time in seconds
        timeout = 0.1
        max_cumulated_wait_time = 15
        wait_time = 0

        while True:
            try:
                trace = q.get(timeout=timeout)
            except Queue.Empty:
                # process queue before shutdown
                if q.empty() and shutdown_event.isSet():
                    logger.info("%s thread has caught *shutdown_event*" %
                                self.__class__.__name__)
                    sys.exit(0)

                wait_time += timeout
                if wait_time > max_cumulated_wait_time:
                    if len(self.data) == 0:
                        # no data from seedlink thread
                        logger.info('Timer reached (%ds)' % max_cumulated_wait_time
                                    + '. No data coming from seedlink thread!'
                                    + ' Network/connection down ?')
                    else:
                        # force data flush to influxdb
                        # even if data block is not completed
                        logger.info('Timer reached (%ds)' % max_cumulated_wait_time
                                    + '. Force data flush to influxdb '
                                    + '(bsize=%d/%d)!'
                                    % (len(self.data), self.nb_data_max))

                    now = datetime.utcnow()
                    self.make_stats(now)
                    try:
                        self.send_points()
                    except BaseException as e:
                        self.force_shutdown(e)
                    wait_time = 0
            else:
                data_pushed = self.manage_data(trace)
                q.task_done()
                if data_pushed:
                    wait_time = 0


class DelayInfluxDBExporter(InfluxDBExporter):
    def __init__(self, host, port,
                 dbname, user, pwd, dropdb=False,
                 geohash={}):
        super(DelayInfluxDBExporter, self).__init__(host, port,
                                                    dbname, user, pwd,
                                                    dropdb, geohash)
        self.refresh_rate = 1.  # sec.

    def make_line_channel_delay(self, channel, packet_time):
        """http://www.seiscomp3.org/doc/jakarta/current/apps/scqc.html"""
        now = datetime.utcnow()
        t = timegm(now.utctimetuple()) * 1e9 \
            + now.microsecond * 1e3
        t_str = str(int(t))

        if packet_time['previous'] is None:
            return

        delay =  packet_time['last'] - packet_time['previous']

        try:
            geohash_tag = ",geohash=%s" % self.geohash[channel]
        except:
            geohash_tag = ""

        s = "delay,channel=%s" % channel + \
            geohash_tag + \
            " value=%.2f " % delay + \
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
        except BaseException as e:
            self.force_shutdown(e)
        return True

    def run(self):
        while True:
            self.manage_data()
            shutdown_event.wait(self.refresh_rate)
            if shutdown_event.isSet():
                logger.info("%s thread has catched *shutdown_event*" %
                            self.__class__.__name__)
                sys.exit(0)

