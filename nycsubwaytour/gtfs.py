from dataclasses import dataclass
from io import BytesIO
import itertools
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Iterator, Optional
import urllib.request
from zipfile import ZipFile

from tqdm import tqdm


@dataclass(frozen=True, slots=True, unsafe_hash=True)
class Stop:
    stop_id: str
    name: str
    lat: float
    lon: float
    location_type: Optional[int]
    parent_station: Optional[str]

    @classmethod
    def parse(cls, line: str) -> "Stop":
        stop_id, name, lat, lon, location_type, parent_station = line.strip().split(",")
        try:
            location_type = int(location_type)
        except ValueError:
            location_type = None
        parent_station = parent_station.strip()
        if not parent_station:
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


class Edge:
    def __init__(self, from_id: str, to_id: str, duration: float, intermediate_stops: Iterable[str] = ()):
        self.from_id: str = from_id
        self.to_id: str = to_id
        self.duration: float = duration
        self.intermediate_stops: [str] = list(intermediate_stops)

    def __hash__(self):
        return hash((self.from_id, self.to_id))

    def __eq__(self, other):
        return isinstance(other, Edge) and other.from_id == self.from_id and other.to_id == self.to_id


class DoTransfer(Edge):
    pass


class Feed:
    def __init__(self, stops: Iterable[Stop], transfers: Iterable[Transfer], edges: Iterable[Edge]):
        self.transfers: {str: {str: Transfer}} = {}
        for transfer in transfers:
            if transfer.from_stop not in self.transfers:
                self.transfers[transfer.from_stop] = {transfer.to_stop: transfer}
            else:
                self.transfers[transfer.from_stop][transfer.to_stop] = transfer

        all_stops: {str: Stop} = {
            stop.stop_id: stop
            for stop in stops
        }
        self.stop_equivalents: {str: str} = {}
        for stop_id, stop in all_stops.items():
            while stop.parent_station is not None:
                stop = all_stops[stop.parent_station]
            self.stop_equivalents[stop_id] = stop.stop_id
        self.stops: {str: Stop} = {
            stop.stop_id: stop
            for stop in all_stops.values()
            if stop.parent_station is None
        }

        self.edges: {str: {str: Edge}} = {}
        for edge in edges:
            from_stop = self.stop_equivalents[edge.from_id]
            to_stop = self.stop_equivalents[edge.to_id]
            edge.from_id = from_stop
            edge.to_id = to_stop
            edge.intermediate_stops = [self.stop_equivalents[s] for s in edge.intermediate_stops]
            if from_stop not in self.edges:
                self.edges[from_stop] = {to_stop: edge}
            else:
                self.edges[from_stop][to_stop] = edge

        # Remove any stops that have no neighbors
        islanded_stops = {
            stop
            for stop in self.stops.keys()
            if sum(1 for _ in self.neighbors(stop)) == 0
        }
        for stop in islanded_stops:
            del self.stops[stop]

        self._shortest_path_lengths: Optional[dict[str: dict[str: float]]] = None

    @property
    def shortest_path_lengths(self) -> dict[str: dict[str: float]]:
        if self._shortest_path_lengths is not None:
            return self._shortest_path_lengths
        self._shortest_path_lengths = {}
        apsp_path = Path("shortest_path_lengths.txt")
        if apsp_path.exists():
            with open(apsp_path, "r") as f:
                for line in f:
                    from_stop, to_stop, distance = (s.strip() for s in line.strip().split(","))
                    distance = float(distance)
                    if from_stop not in self._shortest_path_lengths:
                        self._shortest_path_lengths[from_stop] = {to_stop: distance}
                    else:
                        self._shortest_path_lengths[from_stop][to_stop] = distance
        else:
            ordered_stops = list(self.stops.keys())
            self._shortest_path_lengths: dict[str: dict[str: float]] = {
                from_stop: {
                    to_stop: self.distance(from_stop, to_stop)
                    for to_stop in ordered_stops
                }
                for from_stop in ordered_stops
            }
            for k in tqdm(ordered_stops, leave=False, unit="stops", desc="calculating shortest paths"):
                for i in ordered_stops:
                    for j in ordered_stops:
                        dist = self._shortest_path_lengths[i][k] + self._shortest_path_lengths[k][j]
                        if self._shortest_path_lengths[i][j] > dist:
                            self._shortest_path_lengths[i][j] = dist
            with open(apsp_path, "w") as f:
                for from_stop, lengths in self._shortest_path_lengths.items():
                    for to_stop, distance in lengths.items():
                        f.write(f"{from_stop},{to_stop},{distance}\n")
        for from_node, distances in self._shortest_path_lengths.items():
            for to_node, distance in distances.items():
                if distance >= float('inf'):
                    raise ValueError(f"There is no path from {from_node} to {to_node}!")
        return self._shortest_path_lengths

    def distance(self, from_stop: str, to_stop: str) -> float:
        if from_stop == to_stop:
            return 0
        d = float('inf')
        if from_stop in self.edges and to_stop in self.edges[from_stop]:
            d = self.edges[from_stop][to_stop].duration
        if from_stop in self.transfers and to_stop in self.transfers[from_stop]:
            d = min(d, self.transfers[from_stop][to_stop].min_transfer_time)
        return d

    def neighbors(self, from_stop: str) -> Iterator[Edge]:
        if from_stop in self.edges:
            yield from self.edges[from_stop].values()
        if from_stop in self.transfers:
            for to_stop, transfer in self.transfers[from_stop].items():
                if from_stop != to_stop:
                    yield DoTransfer(from_stop, to_stop, transfer.min_transfer_time)

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
        edges: dict[tuple[str, str], list[int]] = {}
        trips: dict[str, list[str]] = {}
        trips_by_stop: dict[str, set[str]] = {}
        with open(path_or_url / "stop_times.txt") as f:
            # skip the first line because it is a header
            _ = next(iter(f))
            last_trip_id = ""
            last_seq = -1
            last_stop_id = -1
            last_arrival_time = 0
            for line in f:
                trip_id, stop_id, arrival_time, departure_time, stop_sequence = line.strip().split(",")
                trip_id = trip_id.strip()
                if stop_id not in trips_by_stop:
                    trips_by_stop[stop_id] = {trip_id}
                else:
                    trips_by_stop[stop_id].add(trip_id)
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
                if trip_id not in trips:
                    trips[trip_id] = [stop_id]
                else:
                    trips[trip_id].append(stop_id)
        edges: list[Edge] = [
            Edge(from_id, to_id, sum(times) / len(times))
            for (from_id, to_id), times in edges.items()
        ]
        # is there any trip where we pass through a station (e.g., an express train?)
        for edge in tqdm(edges, desc="Finding intermediate stops...", unit="edges", leave=False):
            intermediates: set[tuple[str, ...]] = set()
            for trip_id in trips_by_stop[edge.from_id] | trips_by_stop[edge.to_id]:
                trip = trips[trip_id]
                try:
                    from_id_index = trip.index(edge.from_id)
                    to_id_index = trip.index(edge.to_id)
                except ValueError:
                    continue
                intermediate_stops = tuple(trip[from_id_index+1:to_id_index])
                if intermediate_stops:
                    intermediates.add(intermediate_stops)
            if len(intermediates) > 1:
                # TODO: Find a better way to do this!
                intermediates = {tuple(itertools.chain(*intermediates))}
            if intermediates:
                edge.intermediate_stops = list(next(iter(intermediates)))
        with open(path_or_url / "stops.txt") as f:
            # skip the first line because it is a header
            _ = next(iter(f))
            with open(path_or_url / "transfers.txt") as t:
                _ = next(iter(t))
                return cls(stops=map(Stop.parse, f), transfers=map(Transfer.parse, t), edges=edges)
