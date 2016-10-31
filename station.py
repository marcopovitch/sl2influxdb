#!/usr/bin/env python
import sys
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import Geohash
import logging

# default logger
logger = logging.getLogger('StationCoordInfo')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class StationCoordInfo(object):
    def __init__(self, fdsn_server, streams):
        self.fdsn_server = fdsn_server
        self.streams = streams
        self.station_coordinfo = {}
        self.get_inventory()
        self.geohash = self.get_geohash()

    def get_inventory(self):
        starttime = UTCDateTime()
        endtime = UTCDateTime()
        client = Client(self.fdsn_server)
        for s in self.streams:
            net, sta, chan, loc = s
            inv = client.get_stations(starttime=starttime,
                                      endtime=endtime,
                                      network=net,
                                      station=sta,
                                      location=loc,
                                      channel=chan,
                                      level="response")
            channels = set(inv.get_contents()['channels'])

            for c in channels:
                try:
                    coords = inv.get_coordinates(c, datetime=starttime)
                except:
                    try:
                        coords = inv.get_coordinates(c)
                    except:
                        print c, "No matching coordinates found"
                        continue

                latitude = coords['latitude']
                longitude = coords['longitude']
                elevation = coords['elevation']
                self.station_coordinfo[c] = \
                    {"latitude": latitude,
                     "longitude": longitude,
                     "elevation": elevation,
                     "geohash": Geohash.encode(latitude,
                                               longitude,
                                               precision=7)
                     }

    def get_geohash(self):
        """ Extract only geohash info """
        geohash_dict = {}
        for channel in self.station_coordinfo.keys():
                h = self.station_coordinfo[channel]['geohash']
                geohash_dict[channel] = h
        return geohash_dict

    def show_geohash(self):
        for c in self.geohash.keys():
            logger.info('%s: %s' % (c, self.geohash[c]))

    def show_station_coordinfo(self):
        for channel in self.station_coordinfo.keys():
                info = self.station_coordinfo[channel]
                logger.debug("%s (%f, %f, %f) %s | %s",
                             channel,
                             info['latitude'],
                             info['longitude'],
                             info['elevation'],
                             info['geohash'], 
                             Geohash.decode(info['geohash']))


if __name__ == '__main__':
    streams = [('FR', '*', 'HHZ', '00')]
    info_sta = StationCoordInfo("RESIF", streams)
    # info_sta.show_station_coordinfo()
    print info_sta.get_geohash()

