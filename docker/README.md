# Using docker-compose



## Requirements
* docker pull influxdb
* docker pull grafana/grafana:master


## Build


To build all the containers :
<pre>docker-compose build</pre>



## Data storage
If you are running this project for the first time, you have to create a *influxdb data docker volume* in order to keep your measurements between restarts :

<pre>
docker volume create --name=sl2influxdb_influxdb_data
</pre>


## Start services

### For RaspberryShake
This configuration is ready to be run, assuming your raspeberryshake is in you local network and
reachable using *raspberryshake.local* address.

To start all the containers (influxdb, seedlink fetcher and grafana) :
<pre>
docker-compose up -d rshakegrafana
</pre>

Check the logs to see if seedlink data is fetched without problem :
<pre>
docker-compose logs -f sl2raspberryshake
</pre>

### For Generic Seedlink Server
You need to customize the docker-compose.yml file to set properly this environement variables :

* SEEDLINK_SERVER
* FDSN\_WS\_STATION_SERVER
* SEEDLINK_STREAMS (without space !!)

Then, starts the container:
<pre>docker-compose up -d grafana</pre>

To check the logs if seedlink data is fetched well :
<pre>
docker-compose logs -f sl2generic
</pre>

## Acces to grafana interface
Then launch you preferred browser and go to : [http://localhost:3000](http://localhost:3000), with :

* user: admin
* passwd : admin

## Stop services
<pre>docker-compose down -v</pre>
