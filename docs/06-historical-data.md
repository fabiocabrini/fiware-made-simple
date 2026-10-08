# 6. Historical data

Orion keeps only the current value of each attribute. For charts, analyses, and machine learning models, **STH-Comet** keeps the time series in the `mongo-db-sth` database.

**On this page:** [How the history is fed](#how-the-history-is-fed) · [The subscription](#the-subscription) · [Queries](#queries) · [Direct MongoDB access](#direct-mongodb-access) · [Dashboards](#dashboards) · [Retention and limits](#retention-and-limits)

---

## How the history is fed

STH-Comet does not fetch data: it **receives notifications** from Orion. Each attribute that needs a history requires a *subscription* telling Orion to notify STH-Comet when the value changes. In the collection, this subscription is created in step **2.6**.

```
IoT Agent ──updates──▶ Orion ──notifies (subscription)──▶ STH-Comet ──stores──▶ mongo-db-sth
```

## The subscription

```json
{
  "description": "Notify STH-Comet of all luminosity changes",
  "subject": {
    "entities": [{ "id": "urn:ngsi-ld:Lamp:001", "type": "Lamp" }],
    "condition": { "attrs": ["luminosity"] }
  },
  "notification": {
    "httpCustom": {
      "url": "http://sth-comet:8666/notify",
      "json": {
        "contextResponses": [{
          "contextElement": {
            "id": "${id}", "type": "${type}", "isPattern": "false",
            "attributes": [{ "name": "luminosity", "type": "Integer", "value": "${luminosity}" }]
          },
          "statusCode": { "code": "200", "reasonPhrase": "OK" }
        }]
      }
    },
    "attrs": ["luminosity"]
  }
}
```

**Why `httpCustom`?** STH-Comet only understands notifications in the NGSIv1 format, and Orion 4.x removed the `"attrsFormat": "legacy"` option that produced it. With `httpCustom`, the notification body itself is written in the expected format, and Orion replaces `${id}`, `${type}`, and `${luminosity}` with the real values on every change. Because the *placeholder* takes up the whole value, the number reaches the history as a number and can be aggregated.

**More attributes.** Create **one subscription per attribute**: repeat the body above, replacing `luminosity` with the new attribute (for example, `state`, with `"type": "Text"`). Do not put two attributes in the same subscription: every notification would carry both, and an attribute that did not change would be stored again, duplicated, every time the other one changed, distorting averages and counts.

**Checking.** In `GET /v2/subscriptions` (step 5.1), check `notification.timesSent` (should grow), `lastSuccessCode` (should be `200`), and `lastFailureReason` (reason for the last failure, if any).

## Queries

All queries use the `fiware-service` and `fiware-servicepath` headers and follow this pattern:

```
GET http://<server>:8666/STH/v1/contextEntities/type/<type>/id/<id>/attributes/<attribute>?<parameters>
```

| Goal | Parameters | Example |
|---|---|---|
| Last *N* values (up to 100) | `lastN` | `?lastN=30` |
| Period, paginated (up to 100 per page) | `dateFrom`, `dateTo`, `hLimit`, `hOffset` | `?dateFrom=2026-10-07T00:00:00Z&hLimit=100&hOffset=100` |
| Aggregation | `aggrMethod`, `aggrPeriod` | `?aggrMethod=max&aggrPeriod=hour` |

- `aggrMethod`: `max`, `min`, `sum`, `sum2` (sum of squares), or `occur` (count, for text attributes).
- `aggrPeriod`: `minute`, `hour`, or `day`, the resolutions STH-Comet computes by default. `second` and `month` also exist, but they must be enabled with the STH-Comet `AGGREGATION_BY` variable.
- The mean of a period is `sum / samples`, and the standard deviation can be derived from `sum2`.
- `lastN` and `hLimit` accept at most **100**. For more values, paginate with `hOffset` (0, 100, 200...) or query [MongoDB directly](#direct-mongodb-access).
- Dates are always in ISO 8601 and **UTC** (`recvTime` ends in `Z`).

Example with `curl`:

```bash
curl -H 'fiware-service: smart' -H 'fiware-servicepath: /' \
  'http://localhost:8666/STH/v1/contextEntities/type/Lamp/id/urn:ngsi-ld:Lamp:001/attributes/luminosity?lastN=5'
```

## Direct MongoDB access

For larger analyses, such as Python notebooks, BI tools, or exports, connect to the history database with the **read-only user** defined in `.env`:

```
mongodb://reader:<password>@<server>:27017/?authSource=admin
```

**How the data is organized:**

| Level | Name | Example |
|---|---|---|
| Database | `sth_<fiware-service>` | `sth_smart` |
| Values collection | `sth_<servicepath>_<entityId>_<entityType>` | `sth_/_urn:ngsi-ld:Lamp:001_Lamp` |
| Aggregates collection | the same, with the `.aggr` suffix | `sth_/_urn:ngsi-ld:Lamp:001_Lamp.aggr` |

Each value document looks like this:

```json
{ "recvTime": "2026-10-07T22:12:58.992Z", "attrName": "luminosity", "attrType": "Integer", "attrValue": 84 }
```

**Python example**, with `pip install pymongo pandas`:

```python
import pandas as pd
from pymongo import MongoClient

client = MongoClient("mongodb://reader:PASSWORD@SERVER:27017/?authSource=admin")
collection = client["sth_smart"]["sth_/_urn:ngsi-ld:Lamp:001_Lamp"]

df = pd.DataFrame(collection.find({"attrName": "luminosity"}, {"_id": 0, "recvTime": 1, "attrValue": 1}))
print(df.set_index("recvTime").resample("1min").mean())
```

**MongoDB Compass:** in *New connection*, paste the same URI. The `reader` user sees all the `sth_*` databases but cannot change anything.

> [!TIP]
> If port 27017 is not open to the internet (`STH_MONGO_BIND=127.0.0.1`), use an SSH tunnel and connect to `localhost`:
> ```bash
> ssh -L 27017:localhost:27017 user@server
> ```

## Dashboards

The [`examples/dashboards`](../examples/dashboards/) folder has two ready-made examples that query the STH-Comet API:

- **`dashboard.py`**: an interactive web page (Dash + Plotly) that refreshes by itself.
- **`chart.py`**: a static chart (Matplotlib), in a window or saved as a PNG.

`recvTime` comes in UTC; the examples convert it to the local time zone before displaying it.

## Retention and limits

- STH-Comet is a **short-term** history. By default it keeps everything it receives, with no expiration. Monitor the disk and, if needed, delete the history of an entity with `DELETE /STH/v1/contextEntities/type/<type>/id/<id>` (step 6.2 of the collection).
- **Automatic expiration.** Set in `.env` how many seconds raw values should be kept, and apply it with `docker compose up -d`:

  ```
  STH_EXPIRE_AFTER_SECONDS=2592000   # 30 days
  ```

  STH-Comet creates a TTL index, and MongoDB starts deleting the oldest values by itself. The rule applies to **collections created after the change**. To apply it to an existing collection, use the administrator user:

  ```bash
  docker compose exec mongo-db-sth mongosh -u admin -p ADMIN_PASSWORD --authenticationDatabase admin --eval \
    'db.getSiblingDB("sth_smart").getCollection("sth_/_urn:ngsi-ld:Lamp:001_Lamp").createIndex({recvTime: 1}, {expireAfterSeconds: 2592000})'
  ```

- **Aggregations** (per minute, hour, and day) do not expire. They take little space: one document per attribute and period.
- For large volumes and long retention, FIWARE offers **QuantumLeap** (time series in CrateDB or TimescaleDB) and **Cygnus** (persistence in several databases).

---

[← 5. Smart Lamp PoC](05-smart-lamp.md) · [Index](../README.md#documentation) · Next: [7. Security →](07-security.md)
