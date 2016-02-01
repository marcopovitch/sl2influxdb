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
Latency & traces for multiple stations:

<img src="https://cloud.githubusercontent.com/assets/4367036/12712706/95c4a38c-c8ca-11e5-8fa7-9c40bbdb8d24.png" width="250">

Waveform, RMS, latency plots for a given station:

<img src="https://cloud.githubusercontent.com/assets/4367036/12712707/95e9f498-c8ca-11e5-8115-cabb66dbf692.png" width="250">



## Dependencies:
* [obspy](https://github.com/obspy/obspy/wiki)
* [python InfluxDB](https://github.com/influxdata/influxdb-python)
