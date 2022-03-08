# Seedlink to InfluxDB

Dump seedlink (seismological) time series into [InfluxDB](https://influxdata.com). Use
[Grafana](http://grafana.org) to plot waveforms, real time latency delay, etc. Maps uses
the grafana [worldmap-panel plugin](https://github.com/grafana/worldmap-panel).

Dockerfile, docker-compose.yml are available [here](#using-docker).

## Install

```bash
pip install .
```

## Usage

```bash
~$ seedlink2influxdb -help
Usage: seedlink2influxdb [options]

Options:
  -h, --help            show this help message and exit
  --dbserver=DBSERVER   InfluxDB server name
  --dbport=DBPORT       InfluxDB server port
  --slserver=SLSERVER   seedlink server name
  --slport=SLPORT       seedlink server port
  --fdsnserver=FDSN_SERVER[:PORT]
                        fdsn station server name
  --streams=STREAMS     streams to fetch (regexp): [('.*','.*','.*Z','.*')]
  --flushtime=NUMBER    when to force the data flush to influxdb
  --db=DBNAME           InfluxDB name to use
  --dropdb              [WARNING] drop previous database !
  --keep=NUMBER         how many days to keep data
  --recover             use seedlink statefile to save/get streams from last
```

Example :

```bash
seedlink2influxdb
    --dbserver localhost \
    --dbport 8086 \
    --slserver rtserve.resif.fr \
    --fdsnserver http://ws.resif.fr \
    --db eost2 \
    --keep 1
```

> **Note**
>
> Fdsnserver request (`--fdsnserver` option) is optional. It is only used and performed
> at the begining and *could be slow* (if too much stations info are requested) ! Data
> collected are only used to get station coordinates and are converted to geohash,
> needed to plot measurements on a map.

## Screenshot

### Delay/Latency

Map plugin|Geomap plugin
--------- | ------------
<img src="https://cloud.githubusercontent.com/assets/4367036/22286118/6a4fa65e-e2ee-11e6-93ae-ae1b4f68a7a2.png" width="350"> | <img src="https://user-images.githubusercontent.com/4367036/157223621-29a7d92b-4c7d-40be-8fce-c8a2794e1b8a.png" width="350">


### Dealy Latency board

<img src="https://user-images.githubusercontent.com/4367036/157223937-fce074a2-2500-4f63-b5e7-7adb0342d12e.jpg" width="350">

### Waveform, RMS, latency plots for a given station

<img src="https://cloud.githubusercontent.com/assets/4367036/12712707/95e9f498-c8ca-11e5-8115-cabb66dbf692.png" width="350">

### Traces for multiple stations
<img src="https://user-images.githubusercontent.com/4367036/157225061-275e1f09-5ed6-48bb-95d8-7e7b1ce2f0db.png" width="350">


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

## Dependencies

* [obspy](https://github.com/obspy/obspy/wiki)
* [python InfluxDB](https://github.com/influxdata/influxdb-python)
* [geohash](https://pypi.org/project/python-geohash/)
* [grafana](http://grafana.org) (with [worldmap-panel plugin](https://github.com/grafana/worldmap-panel))

## Using docker

A `docker-compose` is available to quickly setup influxdb and grafana.
Use `docker-compose build` to make docker images.

### Data storage

If you are running this project for the first time, you have to create a
*influxdb data docker volume* in order to keep your measurements between restarts:

```bash
docker volume create --name=sl2influxdb_influxdb_data
```

### Start services

#### For RaspberryShake

This configuration is ready to be run, assuming your raspeberryshake is in you local
network and reachable using *raspberryshake.local* address.

To start all the containers (influxdb, seedlink fetcher and grafana):

```bash
docker-compose up -d rshakegrafana
```

Check the logs to see if seedlink data is fetched without problem:

```bash
docker-compose logs -f sl2raspberryshake
```

#### For Generic Seedlink Server

You need to customize the docker-compose.yml file to set properly this environement
variables:

* SEEDLINK_SERVER
* FDSN_WS_STATION_SERVER
* SEEDLINK_STREAMS (without space !!)

Then, starts the container:

```bash
docker-compose up -d sl2generic
```

To check the logs if seedlink data is fetched well:

```bash
docker-compose logs -f sl2generic
```

### Acces to grafana interface

```bash
docker-compose up -d grafana
```

Some time it may be required to wait for grafana to start since some modules will be installed or upgraded.
Have a look to the log file using :

```bash
docker-compose logs -f grafana
```

When upgrading grafana (eg: version 5 to 5.1 or later) it may be necessary to remove  and create again grafana volumes :
```bash
docker volume rm _grafana_volume_name_
docker volume create --name=_grafana_volume_name_
```
At least removes `_grafana_volume_name_`, when starting containers `docker-compose` will tell you which volume is missing and it will give you the command line to create it.


Then launch you preferred browser and go to
[http://localhost:3000](http://localhost:3000), with:

* user: admin
* passwd : admin

### Stop services

```bash
docker-compose down -v
```
