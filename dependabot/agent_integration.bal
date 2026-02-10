import ballerina/io;
import ballerina/http;

// Record type for agent discovery result
type AgentDiscoveryResult record {|
    string download_url;
    string? version;
    string format;
    string versioning_strategy;
    record {|
        string owner;
        string repo;
        string path;
    |}? github_info;
    string confidence;
    string reasoning;
|};

// Enhanced repository record with agent support
type EnhancedRepository record {|
    string id;
    string vendor;
    string api;
    string name;
    string connector_repo;
    string module_version;
    string frequency;
    string discovery_mode; // "github_verified" | "agent_assisted" | "hybrid"

    record {|
        string? documentation_url;
        record {|
            string owner;
            string repo;
            string spec_path;
            string? release_asset_name;
            string versioning_strategy;
        |}? github;
        string? vendor_api;
    |} sources;

    record {|
        string base_url;
        string documentation_url;
        string description;
        string[] tags;
    |} metadata;

    record {|
        string last_known_version;
        string? last_checked;
        string? last_content_hash;
    |} version_tracking;

    record {|
        string[] hints;
        AgentDiscoveryResult? previous_findings;
    |}? agent_context;
|};

// Agent discovery service
public class AgentDiscoveryService {
    private final string pythonScriptPath;

    public function init(string scriptPath = "agent_discovery.py") {
        self.pythonScriptPath = scriptPath;
    }

    // Call Python agent to discover spec
    public function discoverSpec(
        string vendor,
        string apiName,
        string documentationUrl,
        string[] hints = []
    ) returns AgentDiscoveryResult|error {

        io:println(string `🤖 Invoking AI Agent for ${vendor}/${apiName}...`);

        // Prepare hints as JSON array

        // Call Python script
        // In production, you might want to run this as a separate service
        // For now, we'll use a simple HTTP call to a Python Flask/FastAPI service

        http:Client agentClient = check new("http://localhost:8000");

        json requestPayload = {
            "vendor": vendor,
            "api_name": apiName,
            "documentation_url": documentationUrl,
            "hints": hints
        };

        http:Response response = check agentClient->/discover.post(requestPayload);

        if response.statusCode != 200 {
            return error(string `Agent service returned ${response.statusCode}`);
        }

        json result = check response.getJsonPayload();
        AgentDiscoveryResult discoveryResult = check result.cloneWithType();

        io:println("  ✅ Agent discovery complete");
        io:println(string `  📊 Confidence: ${discoveryResult.confidence}`);

        return discoveryResult;
    }
}

// Enhanced version of your existing monitor that uses agent
public function monitorWithAgent() returns error? {
    io:println("=== Enhanced Dependabot with AI Agent ===\n");

    // Load enhanced registry
    json registryJson = check io:fileReadJson("connector_registry.json");
    map<json> registryMap = check registryJson.cloneWithType();
    json[] connectorsJson = check registryMap.get("connectors").ensureType();
    EnhancedRepository[] connectors = check connectorsJson.cloneWithType();

    io:println(string `Loaded ${connectors.length()} connectors from registry\n`);

    AgentDiscoveryService agent = new();

    // Process each connector based on discovery mode
    foreach EnhancedRepository connector in connectors {
        io:println(string `\n${repeat("=", 60)}`);
        io:println(string `Processing: ${connector.name}`);
        io:println(string `Mode: ${connector.discovery_mode}`);
        io:println(string `${repeat("=", 60)}`);

        if connector.discovery_mode == "agent_assisted" {
            // Use agent to discover spec location
            check processAgentAssistedConnector(connector, agent);

        } else if connector.discovery_mode == "hybrid" {
            // Try GitHub first, use agent as fallback/verification
            check processHybridConnector(connector, agent);

        } else if connector.discovery_mode == "github_verified" {
            // Use existing logic (your current code)
            check processGitHubConnector(connector);
        }

        io:println("");
    }

    io:println("\n✅ Enhanced monitoring complete!");
}

// Process connector using agent discovery
function processAgentAssistedConnector(
    EnhancedRepository connector,
    AgentDiscoveryService agent
) returns error? {

    string? docUrl = connector.sources.documentation_url;

    if docUrl is () {
        io:println("  ⚠️  No documentation URL provided, skipping");
        return;
    }

    // Get hints from agent context
    string[] hints = [];
    if connector.agent_context is record {| string[] hints; AgentDiscoveryResult? previous_findings; |} {
        hints = connector.agent_context?.hints ?: [];
    }

    // Check if we have previous findings to avoid re-discovery
    AgentDiscoveryResult? previousFindings = connector.agent_context?.previous_findings;

    if previousFindings is AgentDiscoveryResult && previousFindings.confidence == "high" {
        io:println("  ℹ️  Using cached discovery result (high confidence)");
        // Use previous findings to download spec
        check downloadAndProcessSpec(connector, previousFindings);
        return;
    }

    // Discover spec location using agent
    AgentDiscoveryResult|error discoveryResult = agent.discoverSpec(
        connector.vendor,
        connector.api,
        docUrl,
        hints
    );

    if discoveryResult is error {
        io:println(string `  ❌ Agent discovery failed: ${discoveryResult.message()}`);
        return discoveryResult;
    }

    // Process based on confidence
    if discoveryResult.confidence == "low" {
        io:println("  ⚠️  Low confidence result, manual review recommended");
        io:println(string `  💡 Reasoning: ${discoveryResult.reasoning}`);
        // Log for manual review
        return;
    }

    // Download and process the spec
    check downloadAndProcessSpec(connector, discoveryResult);

    // Cache the discovery result for future runs
    // In a real system, update the registry file here
    io:println("  💾 Caching discovery result for future runs");
}

// Process hybrid connector (GitHub + Agent verification)
function processHybridConnector(
    EnhancedRepository connector,
    AgentDiscoveryService agent
) returns error? {

    io:println("  🔀 Hybrid mode: Trying GitHub first...");

    // Try GitHub source
    if connector.sources.github is record {| string owner; string repo; string spec_path; string? release_asset_name; string versioning_strategy; |} {
        error? githubResult = processGitHubConnector(connector);

        if githubResult is () {
            io:println("  ✅ GitHub source successful");
            return;
        }

        io:println("  ⚠️  GitHub source failed, trying agent discovery...");
    }

    // Fallback to agent
    if connector.sources.documentation_url is string {
        check processAgentAssistedConnector(connector, agent);
    } else {
        io:println("  ❌ No fallback documentation URL available");
    }
}

// Your existing GitHub processing logic (simplified)
function processGitHubConnector(EnhancedRepository connector) returns error? {
    io:println("  📦 Processing via GitHub...");

    // Use your existing GitHub logic here
    // This would call your existing processReleaseTagRepo, etc.

    return ();
}

// Download and process spec from agent discovery
function downloadAndProcessSpec(
    EnhancedRepository connector,
    AgentDiscoveryResult discovery
) returns error? {

    io:println(string `  📥 Downloading spec from: ${discovery.download_url}`);

    http:Client httpClient = check new(discovery.download_url);
    http:Response response = check httpClient->get("");

    if response.statusCode != 200 {
        return error(string `Failed to download: HTTP ${response.statusCode}`);
    }

    string content = check response.getTextPayload();

    // Determine version
    string version = discovery.version ?: "unknown";

    // Save to standard location: openapi/{vendor}/{api}/{version}/
    string versionDir = string `../openapi/${connector.vendor}/${connector.api}/${version}`;
    string specPath = string `${versionDir}/openapi.${discovery.format}`;

    check saveSpecToFile(content, specPath);

    // Create metadata
    check createMetadata(connector, versionDir);

    io:println(string `  ✅ Spec saved to ${specPath}`);

    return ();
}

// Helper to save spec to file
function saveSpecToFile(string content, string path) returns error? {
    // Implementation here
    return ();
}

// Helper to create metadata
function createMetadata(EnhancedRepository connector, string dir) returns error? {
    // Implementation here
    return ();
}

// Helper to repeat string
function repeat(string s, int times) returns string {
    string result = "";
    foreach int i in 0 ..< times {
        result += s;
    }
    return result;
}
