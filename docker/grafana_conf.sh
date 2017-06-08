curl 'http://admin:admin@192.168.99.100:3000/api/datasources' \
    -X POST \
    -H 'Content-Type: application/json;charset=UTF-8' \
    --data-binary '{"name":"influxdb",
                    "type":"influxdb",
                    "url":"http://192.168.99.100:8086",
                    "access":"direct",
                    "isDefault":true,
                    "database":"eost",
                    "user":"admin",
                    "password":"admin"}'
