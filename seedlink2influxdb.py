#!/usr/bin/env python


import logging
from optparse import OptionParser
from influx import InfluxDBExporter
from seedlink import MySeedlinkClient
from threads import ConsumerThread, ProducerThread

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)


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

    #########################
    # start influxdb thread #
    #########################
    c = ConsumerThread(name='influxdb',
                       dbclient=InfluxDBExporter,
                       args=(options.dbserver,
                             options.dbport,
                             options.dbname,
                             'seedlink', 'seedlink',
                             options.dropdb))
    c.start()

    #########################
    # start seedlink thread #
    #########################

    # forge seedLink server url
    seedlink_url = ':'.join([options.slserver, options.slport])

    # Select a stream and start receiving data : use regexp
    streams = [('FR', '.*', '(HHZ|EHZ)', '00'),
               ('FR', '.*', 'SHZ', ''),
               ('RD', '.*', 'BHZ', '.*'),
               ('(SZ|RT|IG)', '.*', '.*Z', '.*')
               ]

    # streams = [('FR', 'CHIF', 'HHZ', '00')]

    if options.recover:
        statefile = 'statefile.txt'
    else:
        statefile = None

    p = ProducerThread(name='seedlink',
                       slclient=MySeedlinkClient,
                       args=(seedlink_url, streams, statefile))
    p.start()

