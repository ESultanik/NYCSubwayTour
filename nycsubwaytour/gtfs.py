from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Optional
import urllib.request
from zipfile import ZipFile


@dataclass(frozen=True, slots=True, unsafe_hash=True)
class Stop:
    stop_id: str
    name: str
    lat: float
    lon: float
    location_type: Optional[int]
    parent_station: Optional[int]

    @classmethod
    def parse(cls, line: str) -> "Stop":
        stop_id, name, lat, lon, location_type, parent_station = line.strip().split(",")
        try:
            location_type = int(location_type)
        except ValueError:
            location_type = None
        try:
            parent_station = int(parent_station)
        except ValueError:
            parent_station = None
        return cls(
            stop_id=stop_id,
            name=name.strip(),
            lat=float(lat),
            lon=float(lon),
            location_type=location_type,
            parent_station=parent_station
        )


@dataclass(frozen=True, slots=True, unsafe_hash=True)
class Transfer:
    from_stop: str
    to_stop: str
    min_transfer_time: int

    @classmethod
    def parse(cls, line: str) -> "Transfer":
        from_stop_id, to_stop_id, _, min_transfer_time = line.strip().split(",")
        return cls(
            from_stop=from_stop_id.strip(),
            to_stop=to_stop_id.strip(),
            min_transfer_time=int(min_transfer_time),
        )


class Feed:
    def __init__(
            self, stops: Iterable[Stop], transfers: Iterable[Transfer], edges: Iterable[tuple[tuple[int, int], float]]
    ):
        self.stops: {int: Stop} = {
            stop.stop_id: stop
            for stop in stops
        }
        self.transfers: {(int, int): Transfer} = {
            (transfer.from_stop, transfer.to_stop): transfer
            for transfer in transfers
        }
        self.edges: {tuple[int, int]: float} = dict(edges)

    @classmethod
    def load_or_download(cls, download_url: str, path: Optional[Path] = None) -> "Feed":
        if path is None:
            path = Path.cwd()
        if path.exists() and (path.is_file() or path.is_dir() and (path / "stops.txt").exists()):
            return cls.load(path)
        else:
            return cls.load(download_url)

    @classmethod
    def load(cls, path_or_url: Path | str | ZipFile) -> "Feed":
        if isinstance(path_or_url, str):
            if Path(path_or_url).exists():
                return cls.load(Path(path_or_url))
            else:
                # this is a URL
                response = urllib.request.urlopen(path_or_url)
                return cls.load(ZipFile(BytesIO(response.read())))
        elif isinstance(path_or_url, ZipFile):
            with TemporaryDirectory() as d:
                path_or_url.extractall(d)
                return cls.load(d)
        if not isinstance(path_or_url, Path):
            raise ValueError(f"argument must be a Path, str, or ZipFile, not {path_or_url!r}")
        if path_or_url.is_file():
            return cls.load(ZipFile(path_or_url))
        # this is a directory

        edges: {(str, str): [int]} = {}
        with open(path_or_url / "stop_times.txt") as f:
            # skip the first line because it is a header
            _ = next(iter(f))
            last_trip_id = ""
            last_seq = -1
            last_stop_id = -1
            last_arrival_time = 0
            for line in f:
                trip_id, stop_id, arrival_time, departure_time, stop_sequence = line.strip().split(",")
                arrival_hour, arrival_min, arrival_sec = map(int, arrival_time.split(":"))
                arrival_time = arrival_hour * 60 * 60 + arrival_min * 60 + arrival_sec
                stop_sequence = int(stop_sequence)
                if trip_id == last_trip_id and stop_sequence == last_seq + 1:
                    while arrival_time < last_arrival_time:
                        arrival_time += 24 * 60 * 60
                    edge = (last_stop_id, stop_id)
                    if edge not in edges:
                        edges[edge] = [arrival_time - last_arrival_time]
                    else:
                        edges[edge].append(arrival_time - last_arrival_time)
                last_trip_id = trip_id
                last_seq = stop_sequence
                last_stop_id = stop_id
                last_arrival_time = arrival_time

        with open(path_or_url / "stops.txt") as f:
            # skip the first line because it is a header
            _ = next(iter(f))
            with open(path_or_url / "transfers.txt") as t:
                _ = next(iter(t))
                return cls(stops=map(Stop.parse, f), transfers=map(Transfer.parse, t), edges=[
                    (edge, sum(times) / len(times))
                    for edge, times in edges.items()
                ])
