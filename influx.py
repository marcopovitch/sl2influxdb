#!/usr/bin/env python

import sys
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError, \
                                InfluxDBClientError
import requests.exceptions
import logging

# default logger
logger = logging.getLogger('InfluxDBClient')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class InfluxDBExporter(object):
    def __init__(self, host, port,
                 dbname, user, pwd,
                 flushtime,
                 db_management, geohash={}):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.pwd = pwd
        self.flushtime = flushtime
        self.client = None
        self.geohash = geohash

        # holds 'point' to be send to influxdb (1 by line)
        self.data = []

        # max batch size to send:  no more than 5000 (cf. influxdb doc.)
        self.nb_data_max = 5000

        # nb of rqt error before aborting
        self.NB_MAX_TRY_REQUEST = 10

        # get influxdb client
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
        except Exception as e:
            logger.warning(e)
            logger.warning("Can't drop %s database (not existing yet ?)."
                           % dbname)

    def create_db(self, dbname=None):
        if not dbname:
            dbname = self.dbname
        logger.info("Open/Create %s database." % dbname)
        # self.client.create_database(dbname, if_not_exists=True)
        try:
            self.client.create_database(dbname)
        except Exception:
            raise Exception("Can't create database %s" % dbname)

        try:
            self.client.switch_database(dbname)
        except Exception:
            raise Exception("Can't switch to database %s" % dbname)

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
            logger.info("Policy already exists. Changing to new policy !")
            self.client.alter_retention_policy(name,
                                               database=dbname,
                                               duration="%dd" % days,
                                               replication=1,
                                               default=True)

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

    def run(self):
        pass
