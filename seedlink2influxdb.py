#!/usr/bin/env python

# import logging
from optparse import OptionParser
from influx import InfluxDBExporter, DelayInfluxDBExporter
from seedlink import MySeedlinkClient
from station import StationCoordInfo
import threading
from threads import ConsumerThread, ProducerThread, shutdown_event
import signal


def handler(f, s):
    shutdown_event.set()


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
    parser.add_option("--fdsnserver", action="store", dest="fdsn_server",
                      default='RESIF', 
                      help="fdsn station server name")
    parser.add_option("--slport", action="store", dest="slport",
                      default='18000', help="seedlink server port")
    parser.add_option("--db", action="store", dest="dbname",
                      default='RT', help="influxdb name to use")
    parser.add_option("--dropdb",  action="store_true",
                      dest="dropdb", default=False,
                      help="[WARNING] drop previous database !")
    parser.add_option("--keep", action="store", dest="keep",
                      metavar="NUMBER", type="int",
                      default=2, help="how many days to keep data")
    parser.add_option("--recover",  action="store_true",
                      dest="recover", default=False,
                      help="save statefile & try to get stream from last run")
    (options, args) = parser.parse_args()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    ###########
    # geohash #
    ###########
    # Get station coordinates and compute geohash
    # seedlink and fdsn-station do not use the same mask definition :/
    fdsn_streams = [('FR', '*', 'HHZ', '00')]
    info_sta = StationCoordInfo(options.fdsn_server, fdsn_streams)
    station_geohash = info_sta.get_geohash()

    ###################
    # influxdb thread #
    ###################
    # Note: only one influxdb thread should manage database
    # for creation, drop, data rentention

    db_management = {'drop_db': options.dropdb,
                     'retention': options.keep}

    c = ConsumerThread(name='influxdb-latency',
                       dbclient=InfluxDBExporter,
                       args=(options.dbserver,
                             options.dbport,
                             options.dbname,
                             'seedlink',  # user
                             'seedlink',  # pwd
                             db_management, 
                             station_geohash))

    db_management = False  # thread below do not manage db
    d = ConsumerThread(name='influxdb-delay',
                       dbclient=DelayInfluxDBExporter,
                       args=(options.dbserver,
                             options.dbport,
                             options.dbname,
                             'seedlink',  # user
                             'seedlink',  # pwd
                             db_management, 
                             station_geohash))

    ###################
    # seedlink thread #
    ###################

    # forge seedLink server url
    seedlink_url = ':'.join([options.slserver, options.slport])

    # Select a stream and start receiving data : use regexp
    streams = [('FR', '.*', '(HHZ|EHZ)', '00'),
               # ('ND', '.*', 'HHZ', '.*'),
               ('FR', '.*', 'SHZ', ''),
               ('RA', '.*', 'HNZ', '00'),
               ('RD', '.*', 'BHZ', '.*'),
               ('G', '.*', 'BHZ', '.*'),
               # ('XX', '.*', 'BHZ', '.*'),
               ('(SZ|RT|IG|RG)', '.*', '.*Z', '.*')
               ]

    # streams = [('FR', 'CHIF', 'HHZ', '00')]

    statefile = str(options.dbname) + '.statefile.txt'

    p = ProducerThread(name='seedlink-reader',
                       slclient=MySeedlinkClient,
                       args=(seedlink_url, streams, 
                             statefile, options.recover))

    #################
    # start threads #
    #################
    p.start()
    c.start()
    d.start()

    while True:
        threads = threading.enumerate()
        if len(threads) == 1: 
            break
        for t in threads:
            if t != threading.currentThread() and t.is_alive():
                t.join(.1)

    d.join()
    c.join()
    p.join()

