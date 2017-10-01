FROM fabienengels/obspy:latest

MAINTAINER Marc Grunberg <marc.grunberg@unistra.fr>

ENV SL2IDB_DIR /opt/sl2influxdb

WORKDIR /tmp

RUN apt-get update && \
    apt-get install -y --force-yes \
        wget \
        curl \
        unzip && \
    apt-get autoremove && \
    pip install -U pip && \
    pip install influxdb && \
    pip install geohash

RUN mkdir -p $SL2IDB_DIR && \
    wget https://github.com/marcopovitch/sl2influxdb/archive/master.zip && \
    unzip -d $SL2IDB_DIR master.zip && \
    rm -f master.zip

#COPY ./run.sh /run.sh

RUN \
    cp $SL2IDB_DIR/sl2influxdb-master/docker/run.sh /run.sh && \
    chmod +x /run.sh && \
    useradd -ms /bin/bash sysop && \
    chown -R sysop:users $SL2IDB_DIR && \
    mkdir /data && \
    chown sysop:users /data

USER sysop

VOLUME ["/data"]

CMD ["/run.sh"]
