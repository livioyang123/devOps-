"""
Example usage of ConverterService for Docker Compose to Kubernetes conversion

This script demonstrates how to use the ConverterService to convert
Docker Compose files to Kubernetes manifests.
"""

import os
from app.services.converter import ConverterService
from app.services.parser import ParserService
from app.services.llm_router import LLMRouter, ModelParameters
from app.services.llm_providers import OpenAIProvider, OllamaProvider
from app.services.cache import CacheService


# Sample Docker Compose configuration
SAMPLE_COMPOSE = """
version: '3.8'

services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    environment:
      - ENV=production
      - DEBUG=false
    depends_on:
      - db
    volumes:
      - ./html:/usr/share/nginx/html
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_PASSWORD=secret
      - POSTGRES_USER=admin
      - POSTGRES_DB=myapp
    volumes:
      - db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  db_data:

networks:
  default:
    driver: bridge
"""


def main():
    """Main example function"""
    print("=" * 80)
    print("Docker Compose to Kubernetes Converter - Example Usage")
    print("=" * 80)
    print()
    
    # Step 1: Parse Docker Compose
    print("Step 1: Parsing Docker Compose file...")
    parser = ParserService()
    
    try:
        compose = parser.parse_compose(SAMPLE_COMPOSE)
        print(f"✓ Successfully parsed Docker Compose")
        print(f"  - Services: {len(compose.services)}")
        print(f"  - Volumes: {len(compose.volumes)}")
        print(f"  - Networks: {len(compose.networks)}")
        print()
        
        for service in compose.services:
            print(f"  Service: {service.name}")
            print(f"    Image: {service.image}")
            print(f"    Ports: {len(service.ports)}")
            print(f"    Environment: {len(service.environment)} variables")
            print()
    
    except Exception as e:
        print(f"✗ Failed to parse Docker Compose: {e}")
        return
    
    # Step 2: Initialize LLM Router
    print("Step 2: Initializing LLM Router...")
    
    # Check for API keys in environment
    openai_key = os.getenv("OPENAI_API_KEY")
    
    providers = {}
    
    if openai_key:
        print("  ✓ OpenAI provider configured")
        providers['openai'] = OpenAIProvider(api_key=openai_key)
    else:
        print("  ℹ OpenAI API key not found (set OPENAI_API_KEY environment variable)")
    
    # Try Ollama for local models
    try:
        ollama = OllamaProvider()
        providers['ollama'] = ollama
        print("  ✓ Ollama provider configured (local)")
    except Exception:
        print("  ℹ Ollama not available (install and run Ollama for local models)")
    
    if not providers:
        print("\n✗ No LLM providers available. Please configure at least one provider.")
        print("\nOptions:")
        print("  1. Set OPENAI_API_KEY environment variable for OpenAI")
        print("  2. Install and run Ollama for local models")
        return
    
    llm_router = LLMRouter(providers)
    print()
    
    # Step 3: Initialize Cache Service
    print("Step 3: Initializing Cache Service...")
    cache = CacheService()
    
    if cache.health_check():
        print("  ✓ Redis cache connected")
    else:
        print("  ⚠ Redis cache not available (conversion will work but won't be cached)")
    print()
    
    # Step 4: Initialize Converter Service
    print("Step 4: Initializing Converter Service...")
    converter = ConverterService(llm_router, cache)
    print("  ✓ Converter service ready")
    print()
    
    # Step 5: Convert to Kubernetes
    print("Step 5: Converting to Kubernetes manifests...")
    print("  (This may take 10-30 seconds depending on the LLM provider)")
    print()
    
    try:
        # Determine which model to use
        if 'openai' in providers:
            model = 'gpt-4'
            print(f"  Using model: {model}")
        elif 'ollama' in providers:
            model = 'llama2'
            print(f"  Using model: {model} (local)")
        else:
            print("  ✗ No model available")
            return
        
        # Set parameters
        parameters = ModelParameters(
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=4000
        )
        
        # Perform conversion
        manifests, cached, conversion_time = converter.convert_to_k8s(
            compose=compose,
            compose_content=SAMPLE_COMPOSE,
            model=model,
            parameters=parameters
        )
        
        print(f"\n✓ Conversion completed in {conversion_time:.2f}s")
        print(f"  - Cached: {'Yes' if cached else 'No'}")
        print(f"  - Generated manifests: {len(manifests)}")
        print()
        
        # Display manifest summary
        print("Generated Kubernetes Manifests:")
        print("-" * 80)
        
        manifest_types = {}
        for manifest in manifests:
            if manifest.kind not in manifest_types:
                manifest_types[manifest.kind] = []
            manifest_types[manifest.kind].append(manifest.name)
        
        for kind, names in sorted(manifest_types.items()):
            print(f"\n{kind}:")
            for name in names:
                print(f"  - {name}")
        
        print()
        print("-" * 80)
        
        # Display first manifest as example
        if manifests:
            print("\nExample Manifest (first one):")
            print("-" * 80)
            print(manifests[0].content)
            print("-" * 80)
        
        # Save manifests to files
        print("\nSaving manifests to files...")
        output_dir = "k8s_manifests"
        os.makedirs(output_dir, exist_ok=True)
        
        for manifest in manifests:
            filename = f"{output_dir}/{manifest.kind.lower()}-{manifest.name}.yaml"
            with open(filename, 'w') as f:
                f.write(manifest.content)
            print(f"  ✓ Saved: {filename}")
        
        print()
        print("=" * 80)
        print("Conversion completed successfully!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Review the generated manifests in the k8s_manifests/ directory")
        print("  2. Apply to your Kubernetes cluster: kubectl apply -f k8s_manifests/")
        print("  3. Monitor deployment: kubectl get pods")
        print()
    
    except Exception as e:
        print(f"\n✗ Conversion failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
