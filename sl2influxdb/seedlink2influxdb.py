#!/usr/bin/env python3
import argparse
import ast
import logging
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dbserver',
        help="InfluxDB server name",
    )
    parser.add_argument(
        '--dbport',
        help="InfluxDB server port",
        default='8086',
    )
    parser.add_argument(
        '--slserver',
        help="seedlink server name",
        default='renass-fw.u-strasbg.fr',
    )
    parser.add_argument(
        '--slport',
        help="seedlink server port",
        default='18000',
    )
    parser.add_argument(
        '--fdsnserver',
        help="fdsn station server name",
    )
    parser.add_argument(
        '--streams',
        default=default_streams,
        help="streams to fetch (regexp): %s" % default_streams,
    )
    parser.add_argument(
        '--flushtime',
        help="when to force the data flush to influxdb",
        type=int,
        default=15,
    )
    parser.add_argument(
        '--db',
        default='RT',
        help="InfluxDB name to use",
    )
    parser.add_argument(
        '--dropdb',
        help="[WARNING] drop previous database !",
        action='store_true',
    )
    parser.add_argument(
        '--keep',
        help="how many days to keep data",
        type=int,
        default=2,
    )
    parser.add_argument(
        '--recover',
        action="store_true",
        help="use seedlink statefile to save/get streams from last run",
    )
    parser.add_argument(
        '-v', '--verbose',
        help="Can be supplied multiple time to increase verbosity (default: ERROR).",
        action='count',
        default=0,
    )
    args = parser.parse_args()

    db_server = args.dbserver
    db_port = args.dbport
    seedlink_server = args.slserver
    seedlink_port = args.slport
    fdsn_server = args.fdsnserver
    streams = args.streams
    flush_time = args.flushtime
    db_name = args.db
    drop_db = args.dropdb
    retention = args.keep
    recover = args.recover
    verbose = args.verbose

    # Set logging level
    levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    log_level = levels[min(len(levels) - 1, verbose)]
    log_format = '\033[2K%(asctime)s %(name)s: %(levelname)s: %(message)s'
    logging.basicConfig(level=log_level,
                        format=log_format,
                        datefmt="%Y-%m-%d %H:%M:%S")

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    ###########
    # geohash #
    ###########
    # Get station coordinates and compute geohash
    # seedlink and fdsn-station do not use the same mask definition :/
    if fdsn_server:
        logger.info("Get station coordinates from %s" % fdsn_server)
        # fdsn_streams = [('FR', '*', 'HHZ', '00')]
        fdsn_streams = [('*', '*', '*', '*')]
        info_sta = StationCoordInfo(fdsn_server, fdsn_streams)
        station_geohash = info_sta.get_geohash()
    else:
        logger.info("No FDSN server used to get station geoash")
        station_geohash = {}

    ###################
    # influxdb thread #
    ###################
    # Note: only one influxdb thread should manage database
    # for creation, drop, data rentention
    db_management = {
        'drop_db': drop_db,
        'retention': retention,
    }

    c = ConsumerThread(name='traces',
                       dbclient=TraceInfluxDBExporter,
                       args=(db_server,
                             db_port,
                             db_name,
                             'seedlink',  # user
                             'seedlink',  # pwd
                             flush_time,
                             db_management,
                             station_geohash))

    db_management = False  # thread below do not manage db
    # flushtime is mandatory but thread below don't care about it
    d = ConsumerThread(name='latency-delay',
                       dbclient=LatencyDelayInfluxDBExporter,
                       args=(db_server,
                             db_port,
                             db_name,
                             'seedlink',  # user
                             'seedlink',  # pwd
                             flush_time,
                             db_management,
                             station_geohash))

    ###################
    # seedlink thread #
    ###################

    # forge seedLink server url
    seedlink_url = ':'.join([seedlink_server, seedlink_port])

    statefile = '%s.statefile.txt' % db_name

    try:
        mystreams = ast.literal_eval(streams)
    except Exception as e:
        logger.critical('Something went wrong with regexp streams: ' +
                        '%s (%s)' % (streams, e))
        sys.exit(1)

    p = ProducerThread(name='seedlink-reader',
                       slclient=MySeedlinkClient,
                       args=(seedlink_url, mystreams,
                             statefile, recover))

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