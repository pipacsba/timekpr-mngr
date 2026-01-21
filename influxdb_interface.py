from influxdb import InfluxDBClient
from datetime import datetime, timedelta

INFLUX_CFG = {
    "host": "influxdb.lan",
    "port": 8086,
    "database": "home_assistant",
    "ssl": False,
}

client = InfluxDBClient(**INFLUX_CFG)
client.switch_database(INFLUX_CFG["database"])

#usage:
#write_daily_usage(
#    server="server1",
#    user="alice",
#    seconds_used=5432,
#    day=datetime.utcnow(),
#)
def write_daily_usage(server: str, user: str, seconds_used: int, day: datetime):
    point = [{
        "measurement": "timekpr_usage",
        "tags": {
            "server": server,
            "user": user,
        },
        "time": day.replace(hour=0, minute=0, second=0),
        "fields": {
            "seconds": seconds_used,
        }
    }]
    client.write_points(point, time_precision="s")

#Returns
#[
#  {'time': '2026-01-01T00:00:00Z', 'seconds': 3600},
#  {'time': '2026-01-02T00:00:00Z', 'seconds': 1800},
#  ...
#]
def get_last_30_days(server: str, user: str):
    query = f"""
        SELECT sum(seconds) AS seconds
        FROM timekpr_usage
        WHERE server='{server}'
          AND user='{user}'
          AND time >= now() - 30d
        GROUP BY time(1d)
        fill(0)
    """
    result = client.query(query)
    return list(result.get_points())
