from influxdb_client import InfluxDBClient


def get_influxdb_client():
    token = "your_influxdb_token"  # Replace with your InfluxDB token
    org = "your_influxdb_org"  # Replace with your InfluxDB organization
    url = "http://localhost:8086"  # Replace with your InfluxDB URL

    client = InfluxDBClient(url=url, token=token, org=org)
    return client
