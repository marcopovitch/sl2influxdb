# Using docker

## Build Image

<pre>
docker build -t seedlink2influxdb .
</pre>


## Execution

### Needed docker images

This should be done automaticaly when stating services using docker-compose :

* docker pull influxdb
* docker pull grafana/grafana:master

### Environement variables

Mandatory:

* SEEDLINK_SERVER

Optional:

* DB_NAME : influxdb database name
* DROPD : set to 'yes' to start with a clean database
* RECOVER : set to 'yes' to resume seedlink from the last execution (use a statefile)

<pre>
docker run -d --link influxdb:influxdb \
    -e SEEDLINK_SERVER=10.0.0.15 \
    -e DB_NAME=eost \
    -e RECOVER=yes \
    --name seedlink2influxdb seedlink2influxdb
</pre>

# Using docker-compose

## Build
<pre>docker-compose build</pre>

## Data storage

Keep data and configuration files outside container using volume container:

<pre>docker volume create --name=sl2influxdb_influxdb_data
docker volume create --name=sl2influxdb_grafana_conf
docker volume create --name=sl2influxdb_grafana_data</pre>


## Start services
<pre>docker-compose up -d</pre>

I prefer to stick with the original grafana docker image. For the moment, it is not possible to add a grafana data source via ENV variables. Then, to add one (influxdb data souce here) edit accordingly and run once :
<pre>./grafana_conf.sh</pre>


## Stop services
<pre>docker-compose down -v</pre>
