"""Accès aux données InfluxDB (requêtes Flux).

Couche d'accès données : ouvre le client, exécute les requêtes Flux et renvoie des
structures Python simples. La validation des entrées est faite par `core.validation`.
"""
from influxdb_client import InfluxDBClient

from core import config
from core.validation import safe_metric, safe_parcel, safe_range


def client() -> InfluxDBClient:
    return InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN, org=config.INFLUX_ORG)


def ping() -> bool:
    try:
        with client() as c:
            return bool(c.ping())
    except Exception:                              # noqa: BLE001
        return False


def _query(flux: str):
    """Exécute une requête Flux et renvoie les tables résultantes."""
    with client() as c:
        return c.query_api().query(flux)


def query_latest(parcel: str) -> dict:
    parcel = safe_parcel(parcel)
    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "agri_processed" and r.parcel == "{parcel}")
      |> last()
    '''
    fields: dict = {}
    for table in _query(flux):
        for record in table.records:
            fields[record.get_field()] = record.get_value()
            fields["_time"] = record.get_time().isoformat()
    return fields


def query_parcels() -> list:
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.tagValues(bucket: "{config.INFLUX_BUCKET}", tag: "parcel",
      predicate: (r) => r._measurement == "agri_processed", start: -1h)
    '''
    parcels = []
    for table in _query(flux):
        for record in table.records:
            parcels.append(record.get_value())
    return sorted(parcels)


def query_weather() -> dict:
    """Dernières conditions météo du site (mesure `agri_weather`, alimentée par
    le weather-service via Open-Meteo). Mono-site en démo : on prend la dernière
    valeur de chaque champ, tous sites confondus."""
    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -3h)
      |> filter(fn: (r) => r._measurement == "agri_weather")
      |> last()
    '''
    fields: dict = {}
    for table in _query(flux):
        for record in table.records:
            fields[record.get_field()] = record.get_value()
            fields["time"] = record.get_time().isoformat()
            src = record.values.get("source")
            if src:
                fields["source"] = src
    return fields


def query_history(parcel: str, metric: str, rng: str) -> list:
    parcel = safe_parcel(parcel)
    metric = safe_metric(metric)
    rng = safe_range(rng)
    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: {rng})
      |> filter(fn: (r) => r._measurement == "agri_processed"
                        and r.parcel == "{parcel}" and r._field == "{metric}")
      |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
    '''
    points = []
    for table in _query(flux):
        for record in table.records:
            points.append({"time": record.get_time().isoformat(), "value": record.get_value()})
    return points
