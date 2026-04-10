"""
Preservation Property Tests — Conversion with Valid Provider

Property 2: For any ConversionRequest where isBugCondition_Conversion does NOT hold
(a valid LLM provider IS configured), convert_compose_sync MUST return HTTP 200
with a non-empty manifests list — identical to the original (unfixed) behavior.

These tests PASS on UNFIXED code, establishing the baseline that must be preserved
after the fix is applied.

Validates: Requirements 3.1, 3.2
"""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


async def _passthrough_rate_limit(self, request, call_next):
    """Bypass rate limiting in tests so hypothesis runs don't exhaust the bucket."""
    return await call_next(request)


# ---------------------------------------------------------------------------
# Hypothesis strategies — non-bug-condition inputs (valid provider mocked)
# ---------------------------------------------------------------------------

service_strategy = st.fixed_dictionaries({
    "name": st.text(
        alphabet=st.characters(whitelist_categories=("Ll",)),
        min_size=3,
        max_size=12,
    ),
    "image": st.just("nginx:latest"),
    "ports": st.just([{"host": "80", "container": "80", "protocol": "tcp"}]),
    "environment": st.just({}),
    "volumes": st.just([]),
    "depends_on": st.just([]),
    "command": st.none(),
    "networks": st.just([]),
})

compose_structure_strategy = st.fixed_dictionaries({
    "services": st.lists(service_strategy, min_size=1, max_size=2),
    "volumes": st.just([]),
    "networks": st.just([]),
    "version": st.just("3.8"),
})

# Non-bug-condition: model is "gpt-4" but ConverterService is mocked to return manifests
conversion_request_valid = st.fixed_dictionaries({
    "compose_structure": compose_structure_strategy,
    "model": st.just("gpt-4"),
    "parameters": st.just({}),
})


# ---------------------------------------------------------------------------
# Shared mock manifest returned by the fake ConverterService
# ---------------------------------------------------------------------------

MOCK_MANIFEST_YAML = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:latest
"""


def _make_mock_manifests():
    """Return a list of mock KubernetesManifest objects."""
    from app.schemas import KubernetesManifest
    return [
        KubernetesManifest(
            kind="Deployment",
            name="web",
            content=MOCK_MANIFEST_YAML,
            namespace="default",
        )
    ]


def _make_converter_mock(cached: bool = False):
    """
    Return a mock for ConverterService.convert_to_k8s that simulates a valid
    (non-bug-condition) response: HTTP 200 with real manifests.
    """
    manifests = _make_mock_manifests()
    return MagicMock(return_value=(manifests, cached, 0.42))


# ---------------------------------------------------------------------------
# Property tests — valid provider path returns HTTP 200 with manifests
# ---------------------------------------------------------------------------

@given(request_body=conversion_request_valid)
@settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_preservation_valid_provider_returns_200(request_body):
    """
    Property 2 (Preservation): When a valid LLM provider is configured (mocked via
    ConverterService), convert_compose_sync MUST return HTTP 200 with a non-empty
    manifests list.

    Passes on UNFIXED code — establishes baseline that must survive the fix.

    Validates: Requirements 3.1
    """
    from app.main import app

    with patch("app.middleware.RateLimitMiddleware.dispatch", _passthrough_rate_limit), \
         patch("app.services.llm_router.LLMRouter.__init__", return_value=None), \
         patch("app.services.converter.ConverterService.convert_to_k8s",
               _make_converter_mock(cached=False)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/convert/sync", json=request_body)

    assert response.status_code == 200, (
        f"Preservation VIOLATED: expected HTTP 200 with valid provider, "
        f"got {response.status_code}. Body: {response.text}"
    )
    data = response.json()
    assert "manifests" in data, (
        f"Preservation VIOLATED: response missing 'manifests' key. Body: {response.text}"
    )
    assert isinstance(data["manifests"], list) and len(data["manifests"]) > 0, (
        f"Preservation VIOLATED: expected non-empty manifests list, "
        f"got: {data['manifests']!r}"
    )


@given(request_body=conversion_request_valid)
@settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_preservation_valid_provider_manifests_have_kind(request_body):
    """
    Property 2 (Preservation): Each manifest in the response MUST have a 'kind' field.

    Passes on UNFIXED code — establishes baseline manifest structure.

    Validates: Requirements 3.1
    """
    from app.main import app

    with patch("app.middleware.RateLimitMiddleware.dispatch", _passthrough_rate_limit), \
         patch("app.services.llm_router.LLMRouter.__init__", return_value=None), \
         patch("app.services.converter.ConverterService.convert_to_k8s",
               _make_converter_mock(cached=False)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/convert/sync", json=request_body)

    assert response.status_code == 200
    data = response.json()
    for manifest in data.get("manifests", []):
        assert "kind" in manifest, (
            f"Preservation VIOLATED: manifest missing 'kind' field: {manifest!r}"
        )


# ---------------------------------------------------------------------------
# Cache-hit preservation tests
# ---------------------------------------------------------------------------

def test_preservation_cache_hit_returns_200_with_cached_manifests():
    """
    Property 2 (Preservation): When a cached conversion result exists for the
    submitted compose content, convert_compose_sync MUST return HTTP 200 with
    the cached manifests and cached=True.

    Passes on UNFIXED code — establishes cache-hit baseline.

    Validates: Requirements 3.2
    """
    from app.main import app

    request_body = {
        "compose_structure": {
            "services": [
                {
                    "name": "web",
                    "image": "nginx:latest",
                    "ports": [{"host": "80", "container": "80", "protocol": "tcp"}],
                    "environment": {},
                    "volumes": [],
                    "depends_on": [],
                    "command": None,
                    "networks": [],
                }
            ],
            "volumes": [],
            "networks": [],
            "version": "3.8",
        },
        "model": "gpt-4",
        "parameters": {},
    }

    with patch("app.middleware.RateLimitMiddleware.dispatch", _passthrough_rate_limit), \
         patch("app.services.llm_router.LLMRouter.__init__", return_value=None), \
         patch("app.services.converter.ConverterService.convert_to_k8s",
               _make_converter_mock(cached=True)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/convert/sync", json=request_body)

    assert response.status_code == 200, (
        f"Preservation VIOLATED: cache-hit path returned {response.status_code}. "
        f"Body: {response.text}"
    )
    data = response.json()
    assert data.get("cached") is True, (
        f"Preservation VIOLATED: expected cached=True, got cached={data.get('cached')!r}"
    )
    assert isinstance(data.get("manifests"), list) and len(data["manifests"]) > 0, (
        f"Preservation VIOLATED: expected non-empty manifests from cache, "
        f"got: {data.get('manifests')!r}"
    )


def test_preservation_cache_hit_does_not_call_llm():
    """
    Property 2 (Preservation): On a cache hit, convert_to_k8s is called exactly once
    and returns cached=True — the LLM is not invoked by the router.

    Passes on UNFIXED code — establishes that the cache short-circuit is preserved.

    Validates: Requirements 3.2
    """
    from app.main import app
    from app.schemas import KubernetesManifest

    cached_manifests = [
        KubernetesManifest(
            kind="Deployment",
            name="api",
            content=MOCK_MANIFEST_YAML,
            namespace="default",
        )
    ]
    mock_convert = MagicMock(return_value=(cached_manifests, True, 0.01))

    request_body = {
        "compose_structure": {
            "services": [
                {
                    "name": "api",
                    "image": "python:3.11",
                    "ports": [{"host": "8000", "container": "8000", "protocol": "tcp"}],
                    "environment": {},
                    "volumes": [],
                    "depends_on": [],
                    "command": None,
                    "networks": [],
                }
            ],
            "volumes": [],
            "networks": [],
            "version": "3.8",
        },
        "model": "gpt-4",
        "parameters": {},
    }

    with patch("app.middleware.RateLimitMiddleware.dispatch", _passthrough_rate_limit), \
         patch("app.services.llm_router.LLMRouter.__init__", return_value=None), \
         patch("app.services.converter.ConverterService.convert_to_k8s", mock_convert):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/convert/sync", json=request_body)

    assert response.status_code == 200
    data = response.json()
    assert data.get("cached") is True
    mock_convert.assert_called_once()
