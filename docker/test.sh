echo curl "http://${GF_SECURITY_ADMIN_USER}:${GF_SECURITY_ADMIN_PASSWORD}@grafana:3000/api/datasources" \
    -X POST \
    -H 'Content-Type: application/json;charset=UTF-8' \
    --data-binary '`echo {"name":"influxdb",
                          "type":"influxdb",
                          "url":"http://'${INFLUXDB_PORT_8086_TCP_ADDR}':'${INFLUXDB_PORT_8086_TCP_PORT}'",
                          "access":"proxy",
                          "isDefault":true,
                          "database":"'${DB_NAME}'",
                          "user":"admin",
                          "password":"admin"}`'

