FROM debian:9-slim

LABEL maintainer="Marc Grunberg <marc.grunberg@unistra.fr>"

ENV SL2INFLUXDB_DIR /opt/sl2influxdb

COPY sl2influxdb $SL2INFLUXDB_DIR/sl2influxdb
COPY setup.py $SL2INFLUXDB_DIR/
COPY requirements.txt $SL2INFLUXDB_DIR/

WORKDIR $SL2INFLUXDB_DIR

RUN set -ex \
    && buildDeps=' \
        g++ \
        python3-dev \
    ' \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-setuptools \
        $buildDeps \
    ## Install numpy before obspy…
    && pip3 install --no-cache-dir numpy \
    && pip3 install --no-cache-dir --upgrade -r requirements.txt \
    && pip3 install . \
    && apt-get purge -y --autoremove $buildDeps \
    && apt-get clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        $SL2INFLUXDB_DIR

COPY run.sh /run.sh

RUN set -ex \
    && chmod +x /run.sh \
    && useradd -ms /bin/bash sysop \
    && mkdir /data \
    && chown sysop:users /data

USER sysop

ENTRYPOINT ["/run.sh"]
