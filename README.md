# Seedlink to InfluxDB

Dump (seismological) seedlink time series into [InfluxDB](https://influxdata.com). Use [Grafana](http://grafana.org) to plot waveforms, real time latency, etc.

## Usage
<pre>
Usage: seedlink2influxdb.py [options]

Options:
  -h, --help           show this help message and exit
  --dbserver=DBSERVER  InfluxDB server name
  --dbport=DBPORT      db server port
  --slserver=SLSERVER  seedlink server name
  --slport=SLPORT      seedlink server port
  --db=DBNAME          influxdb name to use
  --dropdb             [WARNING] drop previous database !
  --recover            try to get stream from last run
</pre>

## Screenshot 



## Dependencies:
* [obspy](https://github.com/obspy/obspy/wiki)
* [python InfluxDB](https://github.com/influxdata/influxdb-python)
