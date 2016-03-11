#!/bin/bash

set -x

if [ -z "$DB_NAME" ]; then
    DB_NAME="eost"
fi

if [ -z "$RECOVER" ]; then
    EXTRA=""
else
    EXTRA="--recover"
fi

if [ -z "$DROPDB" ]; then
    EXTRA=""
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

cd /data
python $SL2IDB_DIR/sl2influxdb-master/seedlink2influxdb.py \
    --dbserver $INFLUXDB_PORT_8086_TCP_ADDR \
    --dbport $INFLUXDB_PORT_8086_TCP_PORT \
    --slserver $SEEDLINK_SERVER \
    --db $DB_NAME \
    --keep $KEEP \
    $EXTRA


