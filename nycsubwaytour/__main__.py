import argparse
from collections import defaultdict
from pathlib import Path

from .gtfs import Feed, Stop
from .tour import approximate, centrality


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cache", action="store_true", help="do not cache data")
    parser.add_argument("--data-dir", type=Path, default=Path.cwd() / "data",
                        help="data directory (default: ./data)")

    args = parser.parse_args()

    if not args.no_cache:
        cache_path: Path | None = args.data_dir
        cache_path.mkdir(parents=True, exist_ok=True)
    else:
        cache_path = None

    feed = Feed.load_or_download("http://web.mta.info/developers/data/nyct/subway/google_transit.zip", path=cache_path)

    # Get rid of Staten Island!
    for stop in [s for s in feed.stops.keys() if s.startswith("S") and s != "S01"]:
        # print(f"Skipping {feed.stops[stop].name}")
        del feed.stops[stop]
    visits: dict[str: int] = defaultdict(int)
    solution = approximate(feed)
    duration = 0
    prev_stop: Stop = solution[0]
    for i, s in enumerate(solution):
        visits[s] += 1
        if visits[s] > 1:
            num_visits = f" (visit {visits[s]})"
        else:
            num_visits = ""
        if i > 0 and prev_stop.stop_id in feed.transfers and s.stop_id in feed.transfers[prev_stop.stop_id]:
            if s in feed.routes_by_stop:
                route_names = (str(route) for route in feed.routes_by_stop[s])
                print(f"transfer lines {' / '.join(route_names)}")
            else:
                print(f"transfer lines")
        print(f"{i+1:3d} ({duration / 60 / 60:.1f}hrs):\t{s.name}{num_visits}")
        if i > 0:
            duration += feed.shortest_path_lengths[prev_stop.stop_id][s.stop_id]
        prev_stop = s
    print()
    print(f"Minimum expected time: {duration / 60 / 60:.1f}hrs")

    print()
    print("Eigenvector centrality:")
    longest_stop_name = max(
        len(stop.name) for stop in feed.stops.values()
    )
    for c, stop in centrality(feed):
        if c >= 0.0001:
            sn = f"{stop} "
            print(f"{sn:.<{longest_stop_name + 1}} {c:0.4f}")
    return 0


if __name__ == "__main__":
    exit(main())
