from __future__ import annotations

from collections import defaultdict, deque


def dependency_order(node_ids: list[int], edges: list[tuple[int, int]]) -> dict:
    """Return deterministic start/stop orders for workload dependencies.

    Each edge is (upstream, downstream), meaning the downstream workload depends
    on the upstream workload. Start order therefore places upstream services
    first; stop order reverses the start order.

    If a cycle exists, has_cycle is True and the partial topological order is
    returned so callers can block automation and require manual resolution.
    """
    nodes = sorted(set(node_ids))
    indegree = {n: 0 for n in nodes}
    graph: dict[int, list[int]] = defaultdict(list)

    for upstream, downstream in edges:
        if upstream not in indegree or downstream not in indegree:
            continue
        graph[upstream].append(downstream)
        indegree[downstream] += 1

    for key in graph:
        graph[key].sort()

    queue = deque(sorted(n for n, degree in indegree.items() if degree == 0))
    order: list[int] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in graph.get(node, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                # Keep the queue deterministic for documentation and tests.
                queue.append(nxt)
                queue = deque(sorted(queue))

    has_cycle = len(order) != len(nodes)
    unresolved = sorted(set(nodes) - set(order))

    return {
        "has_cycle": has_cycle,
        "start_order": order,
        "stop_order": list(reversed(order)),
        "unresolved": unresolved,
    }
