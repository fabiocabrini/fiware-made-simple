# History dashboards

Two examples that visualize the history stored in STH-Comet:

| Script | Type | When to use it |
|---|---|---|
| [`dashboard.py`](dashboard.py) | Interactive web page (Dash + Plotly), refreshed every 3 seconds | Follow the device in real time |
| [`chart.py`](chart.py) | Static chart (Matplotlib), in a window or a PNG file | Reports, classes, and servers without a graphical interface |

Both query the STH-Comet API (port 8666) and convert the times from UTC to the local time zone. First, create the subscription to STH-Comet (step 2.6 of the collection) and generate a few measurements.

## Installation

Requires Python 3.9 or later. On Ubuntu and Debian, first install virtual environment support with `sudo apt install python3-venv`.

```bash
python3 -m venv .venv            # Windows: py -m venv .venv
```
```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```
```bash
pip install -r requirements.txt
```

## Web dashboard

```bash
python dashboard.py --host SERVER_IP
```

Open http://localhost:8050. The chart keeps the last 200 points, shows the mean, and preserves the zoom between refreshes.

## Static chart

```bash
python chart.py --host SERVER_IP --last-n 60
```
```bash
python chart.py --host SERVER_IP --last-n 60 --save luminosity.png
```

## Common options

| Option | Default | Description |
|---|---|---|
| `--host` | `FIWARE_HOST` variable | IP address or name of the server |
| `--service` / `--servicepath` | `smart` / `/` | `fiware-service` and `fiware-servicepath` headers |
| `--entity-type` / `--entity-id` | `Lamp` / `urn:ngsi-ld:Lamp:001` | Entity to query |
| `--attribute` | `luminosity` | Attribute to query |
| `--last-n` | `30` | Values requested from STH-Comet (maximum 100) |
| `--tz` | this computer's time zone | Display time zone, for example `America/New_York` |

Script-specific options: `dashboard.py` accepts `--interval`, `--max-points`, and `--port`; `chart.py` accepts `--save`.

For more elaborate analyses, such as averages per period or exports, query the history MongoDB directly ([Historical data](../../docs/06-historical-data.md#direct-mongodb-access)).
