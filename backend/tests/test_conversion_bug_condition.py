"""
Bug Condition Exploration Test — Conversion Error Propagation

This test encodes the EXPECTED (fixed) behavior for Bug 1:
  - When no LLM provider is configured, convert_compose_sync SHOULD return HTTP 503
  - The response SHOULD contain a non-empty detail message
  - The response SHOULD NOT contain any manifest content

On UNFIXED code, LLMRouter() is called with no args, raising TypeError caught as
HTTP 500 — so these tests WILL FAIL on unfixed code. That failure CONFIRMS the bug exists.

Validates: Requirements 1.1, 1.2
"""
import os
import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# Ensure no LLM API keys are set for bug condition
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("GOOGLE_API_KEY", None)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

service_strategy = st.fixed_dictionaries({
    "name": st.just("web"),
    "image": st.just("nginx:latest"),
    "ports": st.just([{"host": "80", "container": "80", "protocol": "tcp"}]),
    "environment": st.just({}),
    "volumes": st.just([]),
    "depends_on": st.just([]),
    "command": st.none(),
    "networks": st.just([]),
})

compose_structure_strategy = st.fixed_dictionaries({
    "services": st.lists(service_strategy, min_size=1, max_size=1),
    "volumes": st.just([]),
    "networks": st.just([]),
    "version": st.just("3.8"),
})

# Bug condition: model is "gpt-4" (requires openai provider) and OPENAI_API_KEY is unset
conversion_request_bug_condition = st.fixed_dictionaries({
    "compose_structure": compose_structure_strategy,
    "model": st.just("gpt-4"),
    "parameters": st.just({}),
})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Create a FastAPI TestClient with no LLM providers configured."""
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


@given(request_body=conversion_request_bug_condition)
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_bug_condition_conversion_returns_503_not_500(request_body):
    """
    Property 1 (Bug Condition): When no LLM provider is configured,
    convert_compose_sync MUST return HTTP 503 (not 500).

    On UNFIXED code: LLMRouter() is called with no args → TypeError → HTTP 500
    → this assertion FAILS, confirming the bug exists.

    Validates: Requirements 1.1, 1.2
    """
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/convert/sync", json=request_body)

    # On unfixed code this will be 500, not 503 — test FAILS confirming bug
    assert response.status_code == 503, (
        f"Expected HTTP 503 (no provider configured) but got {response.status_code}. "
        f"Response body: {response.text}. "
        f"COUNTEREXAMPLE: model={request_body['model']}, "
        f"OPENAI_API_KEY={'set' if os.environ.get('OPENAI_API_KEY') else 'unset'}"
    )


@given(request_body=conversion_request_bug_condition)
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_bug_condition_conversion_detail_is_non_empty(request_body):
    """
    Property 1 (Bug Condition): The error response MUST contain a non-empty detail string.

    On UNFIXED code: returns HTTP 500 with a generic message — this assertion may pass
    but the status_code assertion above will fail first.

    Validates: Requirements 1.1, 1.2
    """
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/convert/sync", json=request_body)
    data = response.json()

    assert "detail" in data, (
        f"Response missing 'detail' field. Body: {response.text}"
    )
    assert isinstance(data["detail"], str) and len(data["detail"]) > 0, (
        f"Expected non-empty detail string, got: {data['detail']!r}"
    )


@given(request_body=conversion_request_bug_condition)
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_bug_condition_conversion_no_manifest_content(request_body):
    """
    Property 1 (Bug Condition): The error response MUST NOT contain manifest content.
    Specifically, the response body must not have a 'manifests' list with 'kind' keys.

    On UNFIXED code: returns HTTP 500 with no manifests — this assertion may pass,
    but the status_code assertion above will fail first.

    Validates: Requirements 1.1, 1.2
    """
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/convert/sync", json=request_body)
    data = response.json()

    # If manifests are present, none should have a 'kind' key (no real manifest content)
    manifests = data.get("manifests", [])
    for manifest in manifests:
        assert "kind" not in manifest, (
            f"Response contains manifest content despite error. "
            f"Manifest: {manifest}. "
            f"COUNTEREXAMPLE: model={request_body['model']}"
        )


# ---------------------------------------------------------------------------
# Concrete (non-hypothesis) test for direct counterexample documentation
# ---------------------------------------------------------------------------

def test_concrete_bug_condition_gpt4_no_key():
    """
    Concrete test: POST /api/convert/sync with model='gpt-4' and no OPENAI_API_KEY.

    Expected (fixed): HTTP 503 with non-empty detail, no manifests.
    Actual (unfixed): HTTP 500 — CONFIRMS BUG EXISTS.

    Counterexample: {model: "gpt-4", OPENAI_API_KEY: unset}
    """
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)

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

    response = client.post("/api/convert/sync", json=request_body)
    data = response.json()

    print(f"\n[COUNTEREXAMPLE] status_code={response.status_code}, detail={data.get('detail', 'N/A')}")

    # This FAILS on unfixed code (returns 500 instead of 503)
    assert response.status_code == 503, (
        f"BUG CONFIRMED: Expected 503 but got {response.status_code}. "
        f"detail={data.get('detail', 'N/A')}. "
        f"Root cause: LLMRouter() called with no args raises TypeError → caught as HTTP 500."
    )
    assert data.get("detail"), "Expected non-empty detail message"
    assert not data.get("manifests"), "Expected no manifests in error response"
