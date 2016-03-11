# Construction

docker build -t seedlink2influxdb .

# Execution en mode daemon

docker run -d --link influxdb:influxdb -e SEEDLINK_SERVER=10.0.0.15 -e DB_NAME=eost --name seedlink2influxdb seedlink2influxdb
