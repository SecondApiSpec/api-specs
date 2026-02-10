"""
OpenAPI Spec Discovery Agent

This agent reads vendor documentation pages and intelligently discovers
where OpenAPI specifications are located, how to download them, and
what versioning strategy to use.
"""

import anthropic
import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests


@dataclass
class SpecLocation:
    """Represents discovered OpenAPI spec location"""
    download_url: str
    version: Optional[str]
    format: str  # 'yaml' or 'json'
    versioning_strategy: str  # 'release-tag', 'file-based', 'in-spec', 'unknown'
    github_info: Optional[Dict[str, str]]  # If it's from GitHub
    confidence: str  # 'high', 'medium', 'low'
    reasoning: str  # Why the agent thinks this is the right location


class OpenAPIDiscoveryAgent:
    """
    AI Agent that discovers OpenAPI specifications from documentation URLs
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the discovery agent

        Args:
            api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)
        """
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def discover_spec(
        self,
        vendor: str,
        api_name: str,
        documentation_url: str,
        hints: Optional[List[str]] = None
    ) -> SpecLocation:
        """
        Main method: Discover OpenAPI spec location from documentation

        Args:
            vendor: Vendor name (e.g., "salesforce")
            api_name: API name (e.g., "marketing-cloud")
            documentation_url: URL to vendor's documentation
            hints: Optional hints about where to look

        Returns:
            SpecLocation with download URL and metadata
        """
        print(f"🔍 Discovering OpenAPI spec for {vendor}/{api_name}")
        print(f"📄 Documentation URL: {documentation_url}")

        # Step 1: Use web_fetch to get the documentation page
        page_content = self._fetch_documentation(documentation_url)

        # Step 2: Ask Claude to analyze and find the spec
        spec_location = self._analyze_with_claude(
            vendor=vendor,
            api_name=api_name,
            documentation_url=documentation_url,
            page_content=page_content,
            hints=hints or []
        )

        return spec_location

    def _fetch_documentation(self, url: str) -> str:
        """Fetch the documentation page content"""
        try:
            print(f"  📥 Fetching documentation page...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text[:100000]  # Limit to first 100K chars
        except Exception as e:
            print(f"  ❌ Error fetching page: {e}")
            return ""

    def _analyze_with_claude(
        self,
        vendor: str,
        api_name: str,
        documentation_url: str,
        page_content: str,
        hints: List[str]
    ) -> SpecLocation:
        """
        Use Claude to analyze the documentation and find spec location
        """
        print(f"  🤖 Analyzing with Claude...")

        # Build the prompt for Claude
        system_prompt = """You are an expert at finding OpenAPI specifications from vendor documentation.

Your task is to analyze documentation pages and determine:
1. Where the OpenAPI spec file is located
2. How to download it
3. What versioning strategy the vendor uses
4. The format (YAML or JSON)

Return your findings in this exact JSON format:
{
  "download_url": "direct URL to download the spec",
  "version": "version string or null if unknown",
  "format": "yaml or json",
  "versioning_strategy": "release-tag | file-based | in-spec | unknown",
  "github_info": {
    "owner": "github-owner",
    "repo": "repo-name",
    "path": "path/to/spec.yaml"
  } or null,
  "confidence": "high | medium | low",
  "reasoning": "explain why you believe this is correct"
}

Common patterns to look for:
- Links to GitHub repositories with OpenAPI specs
- Direct download links to .yaml or .json files
- API reference sections mentioning "OpenAPI", "Swagger", "OAS"
- Developer resources or API documentation downloads
- Version numbers in URLs or page content
"""

        user_prompt = f"""Find the OpenAPI specification for: {vendor} {api_name}

Documentation URL: {documentation_url}

Hints:
{chr(10).join(f"- {hint}" for hint in hints)}

Documentation page content (truncated):
{page_content[:50000]}

Analyze this page and find where I can download the OpenAPI specification.
Return ONLY valid JSON, no other text."""

        try:
            # Call Claude
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Try to parse JSON (Claude should return clean JSON)
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())

            print(f"  ✅ Analysis complete!")
            print(f"  📊 Confidence: {result.get('confidence', 'unknown')}")
            print(f"  💡 Reasoning: {result.get('reasoning', 'N/A')[:100]}...")

            return SpecLocation(
                download_url=result.get("download_url", ""),
                version=result.get("version"),
                format=result.get("format", "yaml"),
                versioning_strategy=result.get("versioning_strategy", "unknown"),
                github_info=result.get("github_info"),
                confidence=result.get("confidence", "low"),
                reasoning=result.get("reasoning", "")
            )

        except Exception as e:
            print(f"  ❌ Error analyzing with Claude: {e}")
            return SpecLocation(
                download_url="",
                version=None,
                format="yaml",
                versioning_strategy="unknown",
                github_info=None,
                confidence="low",
                reasoning=f"Error during analysis: {str(e)}"
            )

    def verify_spec_url(self, url: str) -> bool:
        """
        Verify that a URL actually returns an OpenAPI spec
        """
        try:
            print(f"  ✓ Verifying spec URL: {url}")
            response = requests.head(url, timeout=10, allow_redirects=True)

            if response.status_code == 200:
                # Try to actually download and parse
                content_response = requests.get(url, timeout=30)
                content = content_response.text

                # Basic validation - look for OpenAPI keywords
                has_openapi = any(keyword in content.lower() for keyword in [
                    '"openapi":', "'openapi':", 'openapi:', 'swagger:'
                ])

                if has_openapi:
                    print(f"  ✅ Valid OpenAPI spec found!")
                    return True

            print(f"  ⚠️  URL returned {response.status_code}, may not be a spec")
            return False

        except Exception as e:
            print(f"  ❌ Error verifying URL: {e}")
            return False


def main():
    """Example usage of the discovery agent"""

    # Initialize agent
    agent = OpenAPIDiscoveryAgent()

    # Example 1: Discover a spec that we don't have in GitHub
    print("\n" + "="*60)
    print("EXAMPLE: Discovering Salesforce Marketing Cloud API")
    print("="*60)

    result = agent.discover_spec(
        vendor="salesforce",
        api_name="marketing-cloud",
        documentation_url="https://developer.salesforce.com/docs/marketing/marketing-cloud/guide/api-documentation.html",
        hints=[
            "Look for OpenAPI or Swagger downloads",
            "Check API reference section",
            "Look for developer resources"
        ]
    )

    print("\n📋 Discovery Results:")
    print(f"  Download URL: {result.download_url}")
    print(f"  Version: {result.version}")
    print(f"  Format: {result.format}")
    print(f"  Versioning Strategy: {result.versioning_strategy}")
    print(f"  GitHub Info: {result.github_info}")
    print(f"  Confidence: {result.confidence}")
    print(f"\n  Reasoning: {result.reasoning}")

    # Verify the URL if found
    if result.download_url and result.confidence in ['high', 'medium']:
        agent.verify_spec_url(result.download_url)


if __name__ == "__main__":
    main()
