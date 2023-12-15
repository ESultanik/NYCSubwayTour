from dataclasses import dataclass
import heapq
from typing import Iterator

from .gtfs import Feed


def heuristic(feed: Feed, from_node: str, remaining_stops: frozenset[str]) -> float:
    leaves = feed.leaves & remaining_stops
    if leaves:
        return sum(
            feed.leaf_branch_length[leaf]
            for leaf in leaves
        )
    else:
        return max(
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
                # the optimal starting point will be a node that has only one neighbor
                if sum(1 for _ in feed.neighbors(stop)) != 1:
                    continue
                remaining = self.remaining_stops - {stop}
                yield SearchNode(
                    path=(stop,),
                    path_cost=0,
                    remaining_stops=remaining,
                    f_cost=heuristic(feed, stop, remaining)
                )
            return
        neighbors = list(feed.neighbors(self.path[-1]))
        # if there are new directions we've never visited, don't yield any place we have already visited
        new_neighbors = [edge for edge in neighbors if edge.to_id in self.remaining_stops]
        for edge in neighbors:
            neighbor = edge.to_id
            duration = edge.duration
            if len(new_neighbors) > 0 and neighbor not in self.remaining_stops:
                # we've already visited this neighbor and there are new ones to try, so skip!
                continue
            cost = self.path_cost + duration
            remaining = self.remaining_stops - {neighbor} - set(edge.intermediate_stops)
            succ = SearchNode(
                path=self.path + (neighbor,),
                path_cost=cost,
                remaining_stops=remaining,
                f_cost=cost + heuristic(feed, neighbor, remaining)
            )
            if len(new_neighbors) == 1:
                yield from succ.successors(feed)
                return
            else:
                yield succ

    def __str__(self):
        return (f"{len(self.path)} stops ({self.path_cost / 60 / 60:.1f}hrs), "
                f"{len(self.remaining_stops)} ({(self.f_cost - self.path_cost) / 60 / 60:.1f}hrs) remaining")


def search(feed: Feed) -> SearchNode:
    queue: [SearchNode] = [SearchNode(remaining_stops=frozenset(feed.stops.keys()))]
    history: dict[tuple[str, frozenset[str]], float] = {}
    i = 0
    pruned = 0
    while queue:
        node = heapq.heappop(queue)
        i += 1
        if i % 1000 == 0:
            print(f"Best so far: {node!s}\tQueued: {len(queue)}\tPruned: {pruned}")
        if not node.remaining_stops:
            return node
        for succ in node.successors(feed=feed):
            state = (succ.path[-1], succ.remaining_stops)
            if state in history:
                if history[state] <= succ.f_cost:
                    pruned += 1
                    continue
            history[state] = succ.f_cost
            heapq.heappush(queue, succ)
    raise ValueError("No solution!")
