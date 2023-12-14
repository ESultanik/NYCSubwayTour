from pathlib import Path
from .gtfs import Feed


def main() -> int:
    Feed.load_or_download("http://web.mta.info/developers/data/nyct/subway/google_transit.zip")
    return 0


if __name__ == "__main__":
    exit(main())
