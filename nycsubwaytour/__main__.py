from collections import defaultdict

from .gtfs import Feed, Stop
from .mapping import animate
from .tour import approximate


def main() -> int:
    feed = Feed.load_or_download("http://web.mta.info/developers/data/nyct/subway/google_transit.zip")
    # Get rid of Staten Island!
    for stop in [s for s in feed.stops.keys() if s.startswith("S") and s != "S01"]:
        # print(f"Skipping {feed.stops[stop].name}")
        del feed.stops[stop]
    visits: dict[str: int] = defaultdict(int)
    solution = approximate(feed)
    duration = 0
    prev_stop: Stop = solution[0]
    waypoints: list[tuple[float, float]] = []
    for i, s in enumerate(solution):
        waypoints.append((s.lat, s.lon))
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
    animate(waypoints, "route.gif")
    return 0


if __name__ == "__main__":
    exit(main())
