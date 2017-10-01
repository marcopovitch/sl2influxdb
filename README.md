# Seedlink to InfluxDB

Dump seedlink (seismological) time series into [InfluxDB](https://influxdata.com). Use [Grafana](http://grafana.org) to plot waveforms, real time latency delay, etc. Maps uses the grafana [worldmap-panel plugin](https://github.com/grafana/worldmap-panel).

Dockerfile, docker-compse.yml are available [here](https://github.com/marcopovitch/sl2influxdb/blob/master/docker/README.md).

## Usage
<pre>
Usage: seedlink2influxdb.py [options]

Options:
  -h, --help            show this help message and exit
  --dbserver=DBSERVER   InfluxDB server name
  --dbport=DBPORT       db server port
  --slserver=SLSERVER   seedlink server name
  --fdsnserver=FDSN_SERVER:PORT
                        fdsn station server name
  --slport=SLPORT       seedlink server port
  --db=DBNAME           influxdb name to use
  --dropdb              [WARNING] drop previous database !
  --keep=NUMBER         how many days to keep data
  --recover             save statefile & try to get stream from last run
</pre>

Example :
<pre>
./seedlink2influxdb.py	--dbserver localhost \
						--dbport 8086 \
						--slserver rtserve.resif.fr \
						--fdsnserver http://ws.resif.fr \
						--db eost2 \
						--keep 1
</pre>

### Note :

Fdsnserver request (`--fdsnserver` option) is optional. It is only used and performed at the begining and *could be slow* (if too much stations info are requested) ! Data collected are only used to get station coordinates and are converted to geohash,  needed to plot measurements on a map.


## Screenshot

Delay/Latency Map

<img src="https://cloud.githubusercontent.com/assets/4367036/22286118/6a4fa65e-e2ee-11e6-93ae-ae1b4f68a7a2.png" width="350">

<!--
<img src="https://cloud.githubusercontent.com/assets/4367036/19850077/d1ad4990-9f56-11e6-83ff-0c5de3587deb.png" width="400">
-->

Latency & traces for multiple stations:

<img src="https://cloud.githubusercontent.com/assets/4367036/12712706/95c4a38c-c8ca-11e5-8fa7-9c40bbdb8d24.png" width="350">

Waveform, RMS, latency plots for a given station:

<img src="https://cloud.githubusercontent.com/assets/4367036/12712707/95e9f498-c8ca-11e5-8115-cabb66dbf692.png" width="350">



## InfluxDB

InluxDB data representation (measurements, tags, fields, timestamps).

Measurements:

* **queue**: internal messages producer queue (seedlink thread) and consumer queue (influxdb exporter thread)
	* tags  
		* **type**=(consumer|producer)
	* field
		* **size**=queue size
	* timestamp

* **count** : amplitude in count (waveforms)
	* tags
		* **channel** = channel name (eg. FR.WLS.00.HHZ)
	* field
		* **value** = amplitude
	* timestamp

* **latency** : seedlink packet propagation time from station to datacenter
	* tags
		* **channel** = channel name
	* field
		* **value** = latency value
	* timestamp

* **delay** : time since last seedlink packet was received
	* tags
		* **channel** = channel name (eg. FR.WLS.00.HHZ)
		* **geohash** = station coordinates geohash formated
	* field
 		* **value** = latency value
	* timestamp


## Dependencies:
* [obspy](https://github.com/obspy/obspy/wiki)
* [python InfluxDB](https://github.com/influxdata/influxdb-python)
* [geohash](https://github.com/vinsci/geohash/)
* [grafana](http://grafana.org) (with [worldmap-panel plugin](https://github.com/grafana/worldmap-panel))
