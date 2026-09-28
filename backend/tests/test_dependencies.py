from app.services.dependencies import dependency_order


def test_dependency_order_is_topological_and_stop_order_is_reverse():
    result = dependency_order(
        [1, 2, 3, 4],
        [
            (1, 2),  # DB -> API
            (2, 3),  # API -> WEB
            (1, 4),  # DB -> REPORTING
        ],
    )
    assert result["has_cycle"] is False
    assert result["start_order"].index(1) < result["start_order"].index(2)
    assert result["start_order"].index(2) < result["start_order"].index(3)
    assert result["stop_order"] == list(reversed(result["start_order"]))


def test_dependency_cycle_is_detected():
    result = dependency_order([1, 2, 3], [(1, 2), (2, 3), (3, 1)])
    assert result["has_cycle"] is True
    assert set(result["unresolved"]) == {1, 2, 3}
