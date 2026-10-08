#!/usr/bin/env python3
"""Static chart of the STH-Comet history (Matplotlib).

Usage:
    python chart.py --host SERVER_IP                    # opens a window with the chart
    python chart.py --host SERVER_IP --last-n 100 --save luminosity.png
"""
import argparse
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


def parse_args():
    p = argparse.ArgumentParser(description="STH-Comet history chart")
    p.add_argument("--host", default=os.getenv("FIWARE_HOST"), help="IP address or name of the FIWARE server (or FIWARE_HOST)")
    p.add_argument("--service", default="smart", help="fiware-service")
    p.add_argument("--servicepath", default="/", help="fiware-servicepath")
    p.add_argument("--entity-type", default="Lamp")
    p.add_argument("--entity-id", default="urn:ngsi-ld:Lamp:001")
    p.add_argument("--attribute", default="luminosity")
    p.add_argument("--last-n", type=int, default=30, help="number of values (1 to 100)")
    p.add_argument("--tz", help="display time zone, e.g. America/New_York (default: this computer's time zone)")
    p.add_argument("--save", metavar="FILE.png", help="saves to a file instead of opening a window")
    args = p.parse_args()
    if not args.host:
        p.error("set the server with --host or with the FIWARE_HOST variable")
    if not 1 <= args.last_n <= 100:
        p.error("--last-n must be between 1 and 100")
    return args


def fetch_history(args):
    url = (f"http://{args.host}:8666/STH/v1/contextEntities/type/{args.entity_type}"
           f"/id/{args.entity_id}/attributes/{args.attribute}")
    headers = {"fiware-service": args.service, "fiware-servicepath": args.servicepath}
    response = requests.get(url, headers=headers, params={"lastN": args.last_n}, timeout=10)
    response.raise_for_status()
    return response.json()["contextResponses"][0]["contextElement"]["attributes"][0]["values"]


def main():
    args = parse_args()
    if args.save:
        import matplotlib
        matplotlib.use("Agg")  # no window: works on servers without a graphical interface
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    values = fetch_history(args)
    if not values:
        raise SystemExit("No values in the history. Was the subscription to STH-Comet created?")

    tz = ZoneInfo(args.tz) if args.tz else datetime.now().astimezone().tzinfo  # local time zone
    times = [datetime.fromisoformat(v["recvTime"].replace("Z", "+00:00")).astimezone(tz) for v in values]
    data = [float(v["attrValue"]) for v in values]
    mean = sum(data) / len(data)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(times, data, marker="o", color="#ea580c", label=args.attribute)
    ax.axhline(mean, color="#2563eb", linestyle="--", label=f"mean: {mean:.1f}")
    ax.set_title(f"{args.attribute} · {args.entity_id} (last {len(data)} values)")
    ax.set_xlabel(f"Time ({args.tz or 'local time'})")
    ax.set_ylabel(args.attribute)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S", tz=tz))
    ax.grid(alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()

    if args.save:
        fig.savefig(args.save, dpi=120)
        print(f"Chart saved to {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
