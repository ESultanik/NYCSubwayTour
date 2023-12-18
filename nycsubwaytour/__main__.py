from .gtfs import Feed, Stop
from .tour import approximate


def main() -> int:
    feed = Feed.load_or_download("http://web.mta.info/developers/data/nyct/subway/google_transit.zip")
    # Get rid of Staten Island!
    for stop in [s for s in feed.stops.keys() if s.startswith("S")]:
        del feed.stops[stop]
    solution = approximate(feed)
    duration = 0
    prev_stop: Stop = solution[0]
    for i, s in enumerate(solution):
        print(f"{i+1:3d} ({duration / 60 / 60:.1f}hrs):\t{s.name}")
        if i > 0:
            duration += feed.shortest_path_lengths[prev_stop.stop_id][s.stop_id]
        prev_stop = s
    print()
    print(f"Minimum expected time: {duration / 60 / 60:.1f}hrs")
    return 0


if __name__ == "__main__":
    exit(main())
