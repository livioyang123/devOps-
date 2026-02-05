"""
Example usage of LLM Router with multiple providers

This script demonstrates how to initialize and use the LLM Router
with different providers (OpenAI, Anthropic, Google, Ollama).

Note: You need to set up API keys in environment variables or .env file
"""

from app.services import (
    LLMRouter,
    ModelParameters,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    OllamaProvider
)
from app.config import settings


def example_basic_usage():
    """Example: Basic usage with a single provider"""
    print("=" * 60)
    print("Example 1: Basic Usage with OpenAI")
    print("=" * 60)
    
    # Initialize providers
    providers = {}
    
    if settings.openai_api_key:
        providers['openai'] = OpenAIProvider(api_key=settings.openai_api_key)
        print("✓ OpenAI provider configured")
    
    if not providers:
        print("⚠ No providers configured. Please set API keys in .env file")
        return
    
    # Create router
    router = LLMRouter(providers=providers)
    
    # Set parameters
    params = ModelParameters(
        temperature=0.7,
        max_tokens=500,
        system_prompt="You are a helpful Kubernetes expert."
    )
    
    # Generate response
    prompt = "Explain what a Kubernetes Deployment is in 2 sentences."
    
    try:
        response = router.generate(
            prompt=prompt,
            model="gpt-4",
            parameters=params
        )
        print(f"\nPrompt: {prompt}")
        print(f"\nResponse: {response}")
    except Exception as e:
        print(f"Error: {e}")


def example_multiple_providers():
    """Example: Using multiple providers with fallback"""
    print("\n" + "=" * 60)
    print("Example 2: Multiple Providers")
    print("=" * 60)
    
    # Initialize all available providers
    providers = {}
    
    if settings.openai_api_key:
        providers['openai'] = OpenAIProvider(api_key=settings.openai_api_key)
        print("✓ OpenAI provider configured")
    
    if settings.anthropic_api_key:
        providers['anthropic'] = AnthropicProvider(api_key=settings.anthropic_api_key)
        print("✓ Anthropic provider configured")
    
    if settings.google_api_key:
        providers['google'] = GoogleProvider(api_key=settings.google_api_key)
        print("✓ Google provider configured")
    
    # Ollama doesn't need API key (local)
    try:
        providers['ollama'] = OllamaProvider(endpoint="http://localhost:11434")
        print("✓ Ollama provider configured (local)")
    except Exception:
        print("⚠ Ollama not available (is it running?)")
    
    if not providers:
        print("⚠ No providers configured")
        return
    
    print(f"\nTotal providers available: {len(providers)}")
    
    # Create router
    router = LLMRouter(providers=providers)
    
    # Try different models
    models_to_try = [
        ("gpt-4", "OpenAI"),
        ("claude-3-sonnet", "Anthropic"),
        ("gemini-pro", "Google"),
        ("llama2", "Ollama")
    ]
    
    params = ModelParameters(temperature=0.7, max_tokens=100)
    prompt = "What is Docker Compose?"
    
    for model, provider_name in models_to_try:
        if provider_name.lower() in providers:
            try:
                print(f"\n--- Testing {provider_name} ({model}) ---")
                response = router.generate(prompt, model, params)
                print(f"Response: {response[:100]}...")
            except Exception as e:
                print(f"Error with {provider_name}: {e}")


def example_retry_logic():
    """Example: Demonstrating retry logic"""
    print("\n" + "=" * 60)
    print("Example 3: Retry Logic with Exponential Backoff")
    print("=" * 60)
    
    providers = {}
    
    if settings.openai_api_key:
        providers['openai'] = OpenAIProvider(api_key=settings.openai_api_key)
    
    if not providers:
        print("⚠ No providers configured")
        return
    
    router = LLMRouter(providers=providers)
    params = ModelParameters(temperature=0.7, max_tokens=100)
    
    print("\nThe router will automatically retry up to 3 times")
    print("with exponential backoff (1s, 2s, 4s) if a request fails.")
    print("\nRetry delays: [1s, 2s, 4s]")
    
    # This will succeed normally
    try:
        response = router.generate(
            "Say hello",
            "gpt-4",
            params,
            retry_count=3
        )
        print(f"\n✓ Request succeeded: {response[:50]}...")
    except Exception as e:
        print(f"\n✗ All retries failed: {e}")


def example_context_window_management():
    """Example: Context window management"""
    print("\n" + "=" * 60)
    print("Example 4: Context Window Management")
    print("=" * 60)
    
    providers = {}
    
    if settings.openai_api_key:
        providers['openai'] = OpenAIProvider(api_key=settings.openai_api_key)
    
    if not providers:
        print("⚠ No providers configured")
        return
    
    router = LLMRouter(providers=providers)
    
    # Create a very large prompt
    large_content = "x" * 50000  # ~12500 tokens
    print(f"\nOriginal content size: {len(large_content)} characters")
    print(f"Estimated tokens: ~{len(large_content) // 4}")
    
    # Manage context window
    managed = router.manage_context_window(large_content, max_tokens=1000)
    print(f"\nManaged content size: {len(managed)} characters")
    print(f"Estimated tokens: ~{len(managed) // 4}")
    
    if "[Content truncated to fit context window]" in managed:
        print("\n✓ Content was truncated to fit within context window")


def example_docker_compose_conversion():
    """Example: Converting Docker Compose to Kubernetes (simulated)"""
    print("\n" + "=" * 60)
    print("Example 5: Docker Compose to Kubernetes Conversion")
    print("=" * 60)
    
    providers = {}
    
    if settings.openai_api_key:
        providers['openai'] = OpenAIProvider(api_key=settings.openai_api_key)
    
    if not providers:
        print("⚠ No providers configured")
        return
    
    router = LLMRouter(providers=providers)
    
    # Sample Docker Compose
    docker_compose = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    environment:
      - ENV=production
"""
    
    params = ModelParameters(
        temperature=0.3,  # Lower temperature for more deterministic output
        max_tokens=2000,
        system_prompt="""You are a Kubernetes expert. Convert Docker Compose 
configurations to Kubernetes manifests following best practices."""
    )
    
    prompt = f"""Convert this Docker Compose configuration to Kubernetes manifests:

{docker_compose}

Generate:
1. Deployment manifest
2. Service manifest
3. ConfigMap for environment variables

Include best practices like health checks and resource limits."""
    
    try:
        print("\nSending conversion request to LLM...")
        response = router.generate(prompt, "gpt-4", params)
        print("\n--- Generated Kubernetes Manifests ---")
        print(response)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LLM Router Examples")
    print("=" * 60)
    
    # Run examples
    example_basic_usage()
    example_multiple_providers()
    example_retry_logic()
    example_context_window_management()
    
    # Uncomment to test actual conversion (requires API key)
    # example_docker_compose_conversion()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
