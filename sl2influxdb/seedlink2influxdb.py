#!/usr/bin/env python3
import ast
import logging
from optparse import OptionParser
import signal
import sys
import threading

from sl2influxdb.delay import LatencyDelayInfluxDBExporter
from sl2influxdb.seedlink import MySeedlinkClient
from sl2influxdb.station import StationCoordInfo
from sl2influxdb.threads import ConsumerThread, ProducerThread, shutdown_event
from sl2influxdb.trace import TraceInfluxDBExporter


# default logger
logger = logging.getLogger('StationCoordInfo')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def handler(f, s):
    shutdown_event.set()


def main():
    # Select a stream and start receiving data : use regexp
    # only Z component
    default_streams = "[('.*','.*','.*Z','.*')]"
    # default_streams = "[('FR', '.*', '(HHZ|EHZ|ELZ)', '.*'),
    #                     ('ND', '.*', 'HHZ', '.*'),
    #                     ('CL', '.*', 'HHZ', '.*'),
    #                     ('FR', '.*', 'SHZ', ''),
    #                     ('RA', '.*', 'HNZ', '00'),
    #                     ('RD', '.*', 'BHZ', '.*'),
    #                     ('G', '.*', 'BHZ', '.*'),
    #                     ('XX', '.*', 'BHZ', '.*'),
    #                     ('(SZ|RT|IG|RG)', '.*', '.*Z', '.*')
    #                    ]"

    # Parse cmd line
    parser = OptionParser()
    parser.add_option("--dbserver", action="store", dest="dbserver",
                      default=None, help="InfluxDB server name")
    parser.add_option("--dbport", action="store", dest="dbport",
                      default='8086', help="InfluxDB server port")
    parser.add_option("--slserver", action="store", dest="slserver",
                      default='renass-fw.u-strasbg.fr',
                      help="seedlink server name")
    parser.add_option("--slport", action="store", dest="slport",
                      default='18000', help="seedlink server port")
    parser.add_option("--fdsnserver", action="store", dest="fdsn_server",
                      default=None,
                      help="fdsn station server name")
    parser.add_option("--streams", action="store", dest="streams",
                      default=default_streams,
                      help="streams to fetch (regexp): " +
                           default_streams)
    parser.add_option("--flushtime", action="store", dest="flushtime",
                      metavar="NUMBER", type="int",
                      default=15,
                      help="when to force the data flush to influxdb")
    parser.add_option("--db", action="store", dest="dbname",
                      default='RT', help="InfluxDB name to use")
    parser.add_option("--dropdb",  action="store_true",
                      dest="dropdb", default=False,
                      help="[WARNING] drop previous database !")
    parser.add_option("--keep", action="store", dest="keep",
                      metavar="NUMBER", type="int",
                      default=2, help="how many days to keep data")
    parser.add_option("--recover",  action="store_true",
                      dest="recover", default=False,
                      help="use seedlink statefile " +
                           "to save/get streams from last run")
    (options, args) = parser.parse_args()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    ###########
    # geohash #
    ###########
    # Get station coordinates and compute geohash
    # seedlink and fdsn-station do not use the same mask definition :/
    if options.fdsn_server:
        logger.info("Get station coordinates from %s" % options.fdsn_server)
        # fdsn_streams = [('FR', '*', 'HHZ', '00')]
        fdsn_streams = [('*', '*', '*', '*')]
        info_sta = StationCoordInfo(options.fdsn_server, fdsn_streams)
        station_geohash = info_sta.get_geohash()
    else:
        logger.info("No FDSN server used to get station geoash")
        station_geohash = {}

    ###################
    # influxdb thread #
    ###################
    # Note: only one influxdb thread should manage database
    # for creation, drop, data rentention
    db_management = {'drop_db': options.dropdb,
                     'retention': options.keep}

    c = ConsumerThread(name='traces',
                       dbclient=TraceInfluxDBExporter,
                       args=(options.dbserver,
                             options.dbport,
                             options.dbname,
                             'seedlink',  # user
                             'seedlink',  # pwd
                             options.flushtime,
                             db_management,
                             station_geohash))

    db_management = False  # thread below do not manage db
    # flushtime is mandatory but thread below don't care about it
    d = ConsumerThread(name='latency-delay',
                       dbclient=LatencyDelayInfluxDBExporter,
                       args=(options.dbserver,
                             options.dbport,
                             options.dbname,
                             'seedlink',  # user
                             'seedlink',  # pwd
                             options.flushtime,
                             db_management,
                             station_geohash))

    ###################
    # seedlink thread #
    ###################

    # forge seedLink server url
    seedlink_url = ':'.join([options.slserver, options.slport])

    statefile = str(options.dbname) + '.statefile.txt'

    try:
        mystreams = ast.literal_eval(options.streams)
    except Exception as e:
        logger.critical('Something went wrong with regexp streams: ' +
                        '%s (%s)' % (options.streams, e))
        sys.exit(1)

    p = ProducerThread(name='seedlink-reader',
                       slclient=MySeedlinkClient,
                       args=(seedlink_url, mystreams,
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


if __name__ == '__main__':
    main()