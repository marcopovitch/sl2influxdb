#!/bin/bash


# redirect set -x (stderr by default) to stdout
set -x
exec 2>&1

# abort on error
set -e

EXTRA=""

if [ -z "$DB_NAME" ]; then
    DB_NAME="eost"
fi

if [ -z "$RECOVER" ]; then
    EXTRA=$EXTRA
else
    EXTRA="--recover"
fi

if [ -z "$DROPDB" ]; then
    EXTRA=$EXTRA
else
    EXTRA="$EXTRA --dropdb"
fi

if [ -z "$KEEP" ]; then
    KEEP="2"
fi

if [ -z $SEEDLINK_SERVER ]; then
    echo "please set SEEDLINK_SERVER env"
    echo "using -e SEEDLINK_SERVER=10.0.0.1"
    exit 1
fi

if [ -z $FDSN_WS_STATION_SERVER ]; then
    FDSN_WS_STATION_SERVER="RESIF"
fi


pid=0

# SIGTERM-handler
term_handler() {
  if [ $pid -ne 0 ]; then
    kill -SIGTERM "$pid"
    wait "$pid"
  fi
  exit 143; # 128 + 15 -- SIGTERM
}

# setup handlers
trap 'kill ${!}; term_handler' SIGTERM

# run application
cd /data
python $SL2IDB_DIR/sl2influxdb-master/seedlink2influxdb.py \
    --dbserver $INFLUXDB_PORT_8086_TCP_ADDR \
    --dbport $INFLUXDB_PORT_8086_TCP_PORT \
    --slserver $SEEDLINK_SERVER \
    --fdsnserver $FDSN_WS_STATION_SERVER \
    --streams $SEEDLINK_STREAMS \
    --db $DB_NAME \
    --keep $KEEP \
    $EXTRA 2>&1  &

pid="$!"

# wait indefinetely
while true
do
  tail -f /dev/null & wait ${!}
done
