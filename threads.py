#!/usr/bin/env python

import threading
import Queue

BUF_SIZE = 1000

# variable shared by threads
q = Queue.Queue(BUF_SIZE)
shutdown_event = threading.Event()
last_packet_time = {}
lock = threading.Lock()


class ProducerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 slclient=None, args=(), kwargs=None, verbose=None):
        super(ProducerThread, self).__init__()
        self.name = name
        self.slclient = slclient(args[0], args[1], args[2])

    def run(self):
        self.slclient.run()


class ConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 dbclient=None, args=(), kwargs=None, verbose=None):
        super(ConsumerThread, self).__init__()
        self.name = name
        self.dbclient = dbclient(args[0], args[1], args[2],
                                 args[3], args[4], args[5])

    def run(self):
        self.dbclient.run()
