#!/usr/bin/env python
import os
import requests
import json

grafana_host = "192.168.99.100"
grafana_port = 3000
grafana_user = "admin"
grafana_password = "admin"

ifdb_host = "influxdb"
ifdb_port = 8086
ifdb_user = "toto"
ifdb_password = "toto"
ifdb_database = "eost"

datasource_name = "influxdb-test2"

grafana_url = os.path.join('http://', '%s:%u' % (grafana_host, grafana_port))
session = requests.Session()
login_post = session.post(os.path.join(grafana_url, 'login'), 
                          data=json.dumps({'user': grafana_user,
                                           'email': '',
                                           'password': grafana_password}),
                          headers={'content-type': 'application/json'})

print login_post.headers

# Get list of datasources
datasources_get = session.get(os.path.join(grafana_url, 'api', 'datasources'))
datasources = datasources_get.json()

# Add new datasource
datasources_put = session.put(os.path.join(grafana_url, 'api', 'datasources'),
                              data=json.dumps({'access': 'direct',
                                               'database': ifdb_database,
                                               'name': datasource_name,
                                               'password': ifdb_password,
                                               'type': 'influxdb_08',
                                               'url': 'http://%s:%u' %
                                                      (ifdb_host, ifdb_port),
                                               'user': ifdb_user}),
                              headers={'content-type': 'application/json'})
