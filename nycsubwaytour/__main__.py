from .gtfs import Feed
from .tour import approximate


def main() -> int:
    feed = Feed.load_or_download("http://web.mta.info/developers/data/nyct/subway/google_transit.zip")
    # Get rid of Staten Island!
    for stop in [s for s in feed.stops.keys() if s.startswith("S")]:
        del feed.stops[stop]
    solution = approximate(feed)
    print("\n".join(s.name for s in solution))
    print()
    min_duration = sum(
        feed.shortest_path_lengths[s1.stop_id][s2.stop_id]
        for s1, s2 in zip(solution, solution[1:])
    )
    print(f"Minimum expected time: {min_duration / 60 / 60:.1f}hrs")
    return 0


if __name__ == "__main__":
    exit(main())
