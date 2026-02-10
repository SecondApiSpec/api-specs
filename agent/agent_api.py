"""
Flask API wrapper for the OpenAPI Discovery Agent

This provides a simple HTTP API that your Ballerina code can call.
Run with: python agent_api.py
"""

from flask import Flask, request, jsonify
from agent_discovery import OpenAPIDiscoveryAgent
import os

app = Flask(__name__)

# Initialize the agent
agent = OpenAPIDiscoveryAgent()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "OpenAPI Discovery Agent"})

@app.route('/discover', methods=['POST'])
def discover_spec():
    """
    Discover OpenAPI spec location

    Request body:
    {
        "vendor": "salesforce",
        "api_name": "marketing-cloud",
        "documentation_url": "https://...",
        "hints": ["optional", "hints"]
    }

    Response:
    {
        "download_url": "https://...",
        "version": "1.0.0",
        "format": "yaml",
        "versioning_strategy": "in-spec",
        "github_info": {...} or null,
        "confidence": "high",
        "reasoning": "..."
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required = ['vendor', 'api_name', 'documentation_url']
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Extract parameters
        vendor = data['vendor']
        api_name = data['api_name']
        documentation_url = data['documentation_url']
        hints = data.get('hints', [])

        # Call the agent
        result = agent.discover_spec(
            vendor=vendor,
            api_name=api_name,
            documentation_url=documentation_url,
            hints=hints
        )

        # Convert to dict
        response = {
            "download_url": result.download_url,
            "version": result.version,
            "format": result.format,
            "versioning_strategy": result.versioning_strategy,
            "github_info": result.github_info,
            "confidence": result.confidence,
            "reasoning": result.reasoning
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/verify', methods=['POST'])
def verify_url():
    """
    Verify that a URL points to a valid OpenAPI spec

    Request body:
    {
        "url": "https://example.com/openapi.yaml"
    }

    Response:
    {
        "valid": true/false,
        "message": "..."
    }
    """
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({"error": "Missing 'url' field"}), 400

        is_valid = agent.verify_spec_url(url)

        return jsonify({
            "valid": is_valid,
            "message": "Valid OpenAPI spec" if is_valid else "Not a valid OpenAPI spec"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Check for API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("⚠️  Warning: ANTHROPIC_API_KEY not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")

    print("\n🚀 Starting OpenAPI Discovery Agent API...")
    print("📡 Running on http://localhost:8000")
    print("\nEndpoints:")
    print("  GET  /health  - Health check")
    print("  POST /discover - Discover spec location")
    print("  POST /verify   - Verify spec URL")
    print("\n")

    app.run(host='0.0.0.0', port=8000, debug=True)
