#!/usr/bin/env python

import sys
import threading
import Queue
import logging
from obspy.clients.seedlink.seedlinkexception import SeedLinkException


# default logger
logger = logging.getLogger('threads')
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# variable shared by threads
BUF_SIZE = 1000000
q = Queue.Queue(BUF_SIZE)
shutdown_event = threading.Event()
last_packet_time = {}
lock = threading.Lock()


class ProducerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 slclient=None, args=(), kwargs=None, verbose=None):
        super(ProducerThread, self).__init__()
        self.name = name
        try:
            self.slclient = slclient(args[0], args[1], args[2], args[3])
        except SeedLinkException as e:
            self.force_shutdown(e)

    def run(self):
        try:
            self.slclient.run()
        except SeedLinkException as e:
            self.force_shutdown(e)

    def force_shutdown(self, msg):
        logger.error(msg)
        logger.error("%s thread has called force_shutdown()" %
                     self.name)
        shutdown_event.set()
        sys.exit(1)


class ConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 dbclient=None, args=(), kwargs=None, verbose=None):
        super(ConsumerThread, self).__init__()
        self.name = name
        try:
            self.dbclient = dbclient(args[0], args[1], args[2],
                                     args[3], args[4], args[5],
                                     args[6], args[7])
        except Exception as e:
            self.force_shutdown(e)

        self.dbclient.force_shutdown = self.force_shutdown

    def run(self):
        self.dbclient.run()

    def force_shutdown(self, msg):
        logger.error(msg)
        logger.error("%s thread has called force_shutdown()" %
                     self.name)
        shutdown_event.set()
        sys.exit(1)
