# TinyFish Web Agent
Requires: TINYFISH_API_KEY environment variable

```
TINYFISH_API_KEY
```

## Pre-flight Check (REQUIRED)
Before making any API call, always run this first to verify the key is available:

```bash
tinyfish auth status
```

If not authenticated, run: `tinyfish auth login`

## Available Commands

### Web Search
Fast, structured web search returning JSON results:
```bash
tinyfish search "your query here"
```

### Web Fetch
Render a page and return clean Markdown/JSON:
```bash
tinyfish fetch https://example.com
tinyfish fetch --format json https://example.com
```

### Web Agent (Multi-step automation)
Autonomous multi-step workflow on live websites:
```bash
tinyfish agent --url https://example.com --goal "Extract product info as JSON: {\"name\": str, \"price\": str}"
```

### Browser Sessions
Stealth Chrome sessions via CDP:
```bash
tinyfish browser --help
```

## REST API Usage

### Basic Extract/Scrape
```bash
curl -N -s -X POST "https://agent.tinyfish.ai/v1/automation/run-sse" \
  -H "X-API-Key: $TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "goal": "Extract product info as JSON: {\"name\": str, \"price\": str, \"in_stock\": bool}"
  }'
```

### Stealth Mode (for bot-protected sites)
```bash
curl -N -s -X POST "https://agent.tinyfish.ai/v1/automation/run-sse" \
  -H "X-API-Key: $TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://protected-site.com",
    "goal": "Extract data as JSON: {\"field\": str}",
    "browser_profile": "stealth"
  }'
```

### Geo-proxied Request
```bash
curl -N -s -X POST "https://agent.tinyfish.ai/v1/automation/run-sse" \
  -H "X-API-Key: $TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://site.com",
    "goal": "Extract pricing as JSON: {\"item\": str, \"price\": str}",
    "browser_profile": "stealth",
    "proxy_config": {"enabled": true, "country_code": "IN"}
  }'
```

## Output
The SSE stream returns `data: {...}` lines. The final result is the event where:
- `type == "COMPLETE"`
- `status == "COMPLETED"`
- Extracted data is in the `resultJson` field

## Best Practices
1. **Specify JSON format**: Always describe the exact structure you want returned
2. **Parallel calls**: When extracting from multiple independent sites, make separate parallel calls
3. **Stealth for protected sites**: Add `"browser_profile": "stealth"` for bot-protected pages
4. **One task per call**: Each independent extraction task should be its own API call
