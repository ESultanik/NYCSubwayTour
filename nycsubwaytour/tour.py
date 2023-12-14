from dataclasses import dataclass
import heapq
from typing import Iterator

from .gtfs import Feed, Stop, Transfer


def heuristic(feed: Feed, from_node: str, remaining_stops: frozenset[str]) -> float:
    return sum(
        feed.shortest_path_lengths[from_node][stop]
        for stop in remaining_stops
    )


@dataclass(frozen=True, slots=True, unsafe_hash=True)
class SearchNode:
    remaining_stops: frozenset[str]
    path: tuple[str, ...] = ()
    path_cost: float = 0.0
    f_cost: float = 0.0

    def __lt__(self, other):
        return self.f_cost < other.f_cost

    def successors(self, feed: Feed) -> Iterator["SearchNode"]:
        if not self.path:
            for stop in feed.stops.keys():
                remaining = self.remaining_stops - {stop}
                yield SearchNode(
                    path=(stop,),
                    path_cost=0,
                    remaining_stops=remaining,
                    f_cost=heuristic(feed, stop, remaining)
                )
            return
        for neighbor, duration in feed.neighbors(self.path[-1]):
            cost = self.path_cost + duration
            remaining = self.remaining_stops - {neighbor}
            yield SearchNode(
                path=self.path + (neighbor,),
                path_cost=cost,
                remaining_stops=remaining,
                f_cost=cost + heuristic(feed, neighbor, remaining)
            )


def search(feed: Feed) -> SearchNode:
    queue: [SearchNode] = [SearchNode(remaining_stops=frozenset(feed.stops.keys()))]
    while queue:
        node = heapq.heappop(queue)
        print(f"Minimum tour duration: {node.f_cost / 60.0 / 60.0} hours")
        if not node.remaining_stops:
            return node
        for succ in node.successors(feed=feed):
            heapq.heappush(queue, succ)
    raise ValueError("No solution!")
