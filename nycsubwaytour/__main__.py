from .gtfs import Feed
from .tour import search


def main() -> int:
    feed = Feed.load_or_download("http://web.mta.info/developers/data/nyct/subway/google_transit.zip")
    print(search(feed))
    return 0


if __name__ == "__main__":
    exit(main())
