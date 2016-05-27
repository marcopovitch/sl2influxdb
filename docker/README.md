# Using docker

## Build Image

<pre>
docker build -t seedlink2influxdb .
</pre>

## Execution en mode daemon

### Environement variables

Mandatory:

* SEEDLINK_SERVER

Optional:

* DB_NAME
* DROPD
* RECOVER

<pre>
docker run -d --link influxdb:influxdb \
    -e SEEDLINK_SERVER=10.0.0.15 \
    -e DB_NAME=eost \
    -e RECOVER=yes \
    --name seedlink2influxdb seedlink2influxdb
</pre>

# Using docker-compose 

## build
<pre>docker-compose build</pre>

## background execution
<pre>docker-compose up -d</pre>

I prefer to stick with the original grafana docker image. For the moment, it is not possible to add a grafana data source via ENV variables. Then, to add one (influxdb data souce here) edit accordingly and run  :
<pre>./grafana_conf.sh</pre>


## stop 
<pre>docker-compose down -v</pre>

