"""
Practical Example: Adding New Connectors with Agent Discovery

This script demonstrates the complete workflow for adding a new connector
to your system when you only know the vendor's documentation URL.
"""

from agent_discovery import OpenAPIDiscoveryAgent
import json


def example_1_simple_discovery():
    """
    Example 1: Discover Zoom Meeting API

    Scenario: You want to add Zoom to your connectors but don't know
    where their OpenAPI spec is located.
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Discovering Zoom Meeting API")
    print("="*70)

    agent = OpenAPIDiscoveryAgent()

    # All you need to provide
    vendor = "zoom"
    api_name = "meetings"
    doc_url = "https://developers.zoom.us/docs/api/"

    print(f"\n📋 Input:")
    print(f"  Vendor: {vendor}")
    print(f"  API: {api_name}")
    print(f"  Documentation: {doc_url}")
    print(f"\n🔍 Running agent discovery...\n")

    result = agent.discover_spec(
        vendor=vendor,
        api_name=api_name,
        documentation_url=doc_url,
        hints=[
            "Look for OpenAPI specification download",
            "Check API Reference section",
            "Look for GitHub repository links"
        ]
    )

    print(f"\n✅ Discovery Complete!")
    print(f"\n📊 Results:")
    print(f"  Download URL: {result.download_url}")
    print(f"  Version: {result.version or 'Will extract from spec'}")
    print(f"  Format: {result.format}")
    print(f"  Versioning Strategy: {result.versioning_strategy}")
    print(f"  Confidence: {result.confidence}")

    if result.github_info:
        print(f"\n🔗 GitHub Info:")
        print(f"  Owner: {result.github_info['owner']}")
        print(f"  Repo: {result.github_info['repo']}")
        print(f"  Path: {result.github_info['path']}")

    print(f"\n💡 Agent's Reasoning:")
    print(f"  {result.reasoning}")

    # Now create the registry entry
    registry_entry = create_registry_entry(vendor, api_name, result, doc_url)

    print(f"\n📝 Registry Entry to Add:")
    print(json.dumps(registry_entry, indent=2))

    return registry_entry


def example_2_multiple_vendors():
    """
    Example 2: Batch discover multiple vendors

    Scenario: You have a list of vendors to add and want to discover
    all their specs at once.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Batch Discovery for Multiple Vendors")
    print("="*70)

    agent = OpenAPIDiscoveryAgent()

    # List of vendors you want to add
    vendors_to_add = [
        {
            "vendor": "shopify",
            "api": "admin",
            "doc_url": "https://shopify.dev/docs/api/admin-rest",
            "hints": ["Look for REST API documentation downloads"]
        },
        {
            "vendor": "square",
            "api": "payments",
            "doc_url": "https://developer.squareup.com/docs/api",
            "hints": ["Check API reference downloads"]
        },
        {
            "vendor": "zendesk",
            "api": "support",
            "doc_url": "https://developer.zendesk.com/api-reference/",
            "hints": ["Look for OpenAPI spec in documentation"]
        }
    ]

    results = []

    for vendor_info in vendors_to_add:
        print(f"\n📦 Processing: {vendor_info['vendor']}/{vendor_info['api']}")

        result = agent.discover_spec(
            vendor=vendor_info["vendor"],
            api_name=vendor_info["api"],
            documentation_url=vendor_info["doc_url"],
            hints=vendor_info["hints"]
        )

        registry_entry = create_registry_entry(
            vendor_info["vendor"],
            vendor_info["api"],
            result,
            vendor_info["doc_url"]
        )

        results.append(registry_entry)

        print(f"  ✅ Confidence: {result.confidence}")
        print(f"  📍 Found at: {result.download_url[:60]}...")

    print(f"\n📋 Summary: Discovered {len(results)} specs")
    print(f"\n💾 Save these entries to your connector_registry.json:")
    print(json.dumps(results, indent=2))

    return results


def example_3_verify_existing():
    """
    Example 3: Verify existing GitHub-based connectors

    Scenario: You have connectors using GitHub, but want to verify
    there aren't better/newer sources available.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Verify Existing Connectors")
    print("="*70)

    agent = OpenAPIDiscoveryAgent()

    # Example: You have Twilio in GitHub but want to verify
    existing_connector = {
        "vendor": "twilio",
        "api": "twilio",
        "github": {
            "owner": "twilio",
            "repo": "twilio-oai",
            "path": "spec/json/twilio_api_v2010.json"
        },
        "doc_url": "https://www.twilio.com/docs/openapi"
    }

    print(f"\n📦 Verifying: {existing_connector['vendor']}/{existing_connector['api']}")
    print(f"  Current source: GitHub - {existing_connector['github']['owner']}/{existing_connector['github']['repo']}")

    result = agent.discover_spec(
        vendor=existing_connector["vendor"],
        api_name=existing_connector["api"],
        documentation_url=existing_connector["doc_url"],
        hints=["Look for official OpenAPI spec sources"]
    )

    print(f"\n🔍 Agent found:")
    print(f"  {result.download_url}")

    if result.github_info:
        existing_match = (
            result.github_info['owner'] == existing_connector['github']['owner'] and
            result.github_info['repo'] == existing_connector['github']['repo']
        )

        if existing_match:
            print(f"\n✅ VERIFIED: Agent confirms your GitHub source is correct!")
        else:
            print(f"\n⚠️  ALERT: Agent found a different source!")
            print(f"     Consider updating to: {result.github_info['owner']}/{result.github_info['repo']}")


def create_registry_entry(vendor, api_name, discovery_result, doc_url):
    """
    Helper: Create a properly formatted registry entry from discovery result
    """

    # Determine discovery mode based on result
    if discovery_result.github_info:
        discovery_mode = "hybrid"  # Has GitHub, but was found via agent
    else:
        discovery_mode = "agent_assisted"

    # Build sources object
    sources = {
        "documentation_url": doc_url
    }

    if discovery_result.github_info:
        sources["github"] = {
            "owner": discovery_result.github_info["owner"],
            "repo": discovery_result.github_info["repo"],
            "spec_path": discovery_result.github_info["path"],
            "versioning_strategy": discovery_result.versioning_strategy
        }

    # Create full entry
    entry = {
        "id": f"{vendor}-{api_name}",
        "vendor": vendor,
        "api": api_name,
        "name": f"{vendor.title()} {api_name.title()} API",
        "connector_repo": f"module-ballerinax-{vendor}.{api_name}",
        "module_version": "1.0.0-SNAPSHOT",
        "frequency": "weekly",
        "discovery_mode": discovery_mode,
        "sources": sources,
        "metadata": {
            "base_url": f"https://api.{vendor}.com",  # Placeholder
            "documentation_url": doc_url,
            "description": f"{vendor.title()} {api_name.title()} API",
            "tags": [vendor, api_name]
        },
        "version_tracking": {
            "last_known_version": discovery_result.version or "unknown",
            "last_checked": None,
            "last_content_hash": None
        },
        "agent_context": {
            "hints": [],
            "previous_findings": {
                "download_url": discovery_result.download_url,
                "version": discovery_result.version,
                "format": discovery_result.format,
                "versioning_strategy": discovery_result.versioning_strategy,
                "github_info": discovery_result.github_info,
                "confidence": discovery_result.confidence,
                "reasoning": discovery_result.reasoning
            }
        }
    }

    return entry


def example_4_connector_from_list():
    """
    Example 4: Process connectors from the list you provided

    This shows how to handle the real connectors from your project.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Processing Real Connectors from Your List")
    print("="*70)

    agent = OpenAPIDiscoveryAgent()

    # These are from your actual connector list
    real_connectors = [
        {
            "name": "module-ballerinax-jira",
            "vendor": "jira",
            "api": "jira",
            "doc_url": "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/"
        },
        {
            "name": "module-ballerinax-zoom.meetings",
            "vendor": "zoom",
            "api": "meetings",
            "doc_url": "https://developers.zoom.us/docs/api/"
        },
        {
            "name": "module-ballerinax-smartsheet",
            "vendor": "smartsheet",
            "api": "smartsheet",
            "doc_url": "https://smartsheet.redoc.ly/"
        }
    ]

    print(f"\n📋 Processing {len(real_connectors)} connectors from your list...\n")

    discovered = []

    for connector in real_connectors[:1]:  # Start with just one for demo
        print(f"🔍 {connector['name']}")

        result = agent.discover_spec(
            vendor=connector["vendor"],
            api_name=connector["api"],
            documentation_url=connector["doc_url"],
            hints=[
                "Look for OpenAPI specification",
                "Check for GitHub repository",
                "Look in API documentation downloads"
            ]
        )

        entry = create_registry_entry(
            connector["vendor"],
            connector["api"],
            result,
            connector["doc_url"]
        )

        discovered.append(entry)

        print(f"  ✅ Found: {result.download_url[:70]}...")
        print(f"  📊 Confidence: {result.confidence}\n")

    return discovered


def main():
    """
    Run all examples
    """
    print("\n" + "="*70)
    print("OpenAPI Discovery Agent - Practical Examples")
    print("="*70)
    print("\nThese examples show you how to use the agent to discover")
    print("OpenAPI specs for connectors in your project.\n")

    choice = input("Which example would you like to run?\n"
                  "1. Simple discovery (Zoom)\n"
                  "2. Batch discovery (multiple vendors)\n"
                  "3. Verify existing connector\n"
                  "4. Process real connectors from your list\n"
                  "5. All examples\n"
                  "\nChoice (1-5): ")

    if choice == "1":
        example_1_simple_discovery()
    elif choice == "2":
        example_2_multiple_vendors()
    elif choice == "3":
        example_3_verify_existing()
    elif choice == "4":
        example_4_connector_from_list()
    elif choice == "5":
        example_1_simple_discovery()
        example_2_multiple_vendors()
        example_3_verify_existing()
        example_4_connector_from_list()
    else:
        print("Invalid choice!")

    print("\n" + "="*70)
    print("Examples complete! Check AGENT_SETUP_GUIDE.md for more details.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
