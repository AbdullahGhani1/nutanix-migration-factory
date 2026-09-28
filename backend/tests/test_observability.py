from app.observability import _route_template


class DummyURL:
    path = "/api/v1/workloads/42"


class DummyRequest:
    def __init__(self, route=None):
        self.scope = {"route": route}
        self.url = DummyURL()


class DummyRoute:
    path = "/api/v1/workloads/{workload_id}"


def test_route_template_uses_route_pattern_to_avoid_high_cardinality():
    assert _route_template(DummyRequest(DummyRoute())) == "/api/v1/workloads/{workload_id}"


def test_route_template_falls_back_to_url_path():
    assert _route_template(DummyRequest()) == "/api/v1/workloads/42"
