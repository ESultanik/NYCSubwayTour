from .gtfs import Feed
from .tour import search


def main() -> int:
    feed = Feed.load_or_download("http://web.mta.info/developers/data/nyct/subway/google_transit.zip")
    # Get rid of Staten Island!
    for stop in [s for s in feed.stops.keys() if s.startswith("S")]:
        del feed.stops[stop]
    print(search(feed).path)
    return 0


if __name__ == "__main__":
    exit(main())
