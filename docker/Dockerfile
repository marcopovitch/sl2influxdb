FROM fabienengels/obspy:latest
MAINTAINER Marc Grunberg <marc.grunberg@unistra.fr>

ENV SL2IDB_DIR /opt/sl2influxdb

WORKDIR /tmp

RUN apt-get install -y \
        wget \
        unzip && \
    pip install influxdb && \
    mkdir -p $SL2IDB_DIR && \
    wget https://github.com/marcopovitch/sl2influxdb/archive/master.zip && \
    unzip -d $SL2IDB_DIR master.zip

COPY run.sh /run.sh

RUN chmod +x /run.sh && \
    useradd -ms /bin/bash sysop && \
    chown -R sysop:users $SL2IDB_DIR && \
    mkdir -p /data && 
    chown sysop:users /data

VOLUME ["/data"]
USER sysop 
CMD ["/run.sh"]
