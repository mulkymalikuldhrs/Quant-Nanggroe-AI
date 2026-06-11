# AI-MultiColony-Ecosystem — Tool Registry

> Cluster 2 Tool Registry Document
> Version: 0.1.0-draft | Status: Pre-Implementation | Classification: Internal

---

## 1. Overview

This document defines the complete tool registry for the AI-MultiColony-Ecosystem.
All tools are exposed via the Model Context Protocol (MCP), providing a unified
interface for agent-to-tool communication. The registry catalogs every tool from
the 19+ audited repositories, external integrations (Composio, public-apis), and
new tools required by the unified architecture.

**Core principle**: Every tool is an MCP server. Agents never access tools directly;
they always go through the MCP client layer. This enables permission control,
audit logging, rate limiting, and transport abstraction.

---

## 2. Tool Taxonomy

### 2.1 Classification Hierarchy

```
TOOLS
├── BROWSER
│   ├── Navigation      (navigate, back, forward, refresh)
│   ├── Interaction     (click, type, hover, drag, scroll)
│   ├── Extraction      (screenshot, extract_text, extract_links, get_dom)
│   ├── Stealth         (fingerprint_mask, proxy_rotate, user_agent_cycle)
│   └── Session         (cookie_manage, local_storage, session_persist)
│
├── COMPUTER-USE
│   ├── Screen          (capture, find_element, read_region)
│   ├── Mouse           (click, double_click, drag, scroll)
│   ├── Keyboard        (type, hotkey, paste)
│   ├── Window          (list, focus, resize, close)
│   └── Application     (launch, quit, menu_select)
│
├── API
│   ├── REST            (get, post, put, patch, delete)
│   ├── GraphQL         (query, mutate)
│   ├── WebSocket       (connect, send, receive)
│   └── Webhook         (register, listen, verify)
│
├── DATA
│   ├── Database        (query_sql, insert, update, delete, migrate)
│   ├── File            (read, write, list, search, transform)
│   ├── Vector          (embed, search, upsert, delete_collection)
│   └── Pipeline        (etl, validate, transform, load)
│
├── CODE
│   ├── Execution       (run_python, run_javascript, run_shell)
│   ├── Package         (install, uninstall, list)
│   ├── Version Control (git_clone, git_commit, git_diff, git_log)
│   └── Build           (compile, test, lint, format)
│
├── MESSAGING
│   ├── Email           (send, read, search, reply)
│   ├── Chat            (slack, discord, teams, telegram, whatsapp)
│   └── Notification    (push, sms, webhook_dispatch)
│
└── INFRASTRUCTURE
    ├── Container       (run, stop, logs, exec, inspect)
    ├── Cloud           (deploy, scale, monitor, configure)
    ├── Network         (dns_lookup, ping, trace, port_scan)
    └── Credential      (store, retrieve, rotate, validate)
```

### 2.2 Tool Priority Classification

| Priority | Definition | SLA | Examples |
|---|---|---|---|
| **P0 - Critical** | System cannot function without | 99.9% uptime, <100ms | Filesystem, code execution, LLM |
| **P1 - Essential** | Core agent workflows depend on | 99.5% uptime, <500ms | Browser, API calls, database |
| **P2 - Valuable** | Significantly enhances capability | 99% uptime, <1s | Computer-use, messaging, vector search |
| **P3 - Nice-to-have** | Supplementary functionality | Best-effort | Geolocation, webhooks, niche APIs |

---

## 3. MCP Tool Integration Strategy

### 3.1 MCP Architecture

```
┌───────────────────────────────────────────────────────────┐
│                     MCP CLIENT LAYER                      │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  MCP Client Manager                                 │  │
│  │  - Connection pooling                               │  │
│  │  - Health checking                                  │  │
│  │  - Rate limiting                                    │  │
│  │  - Request routing                                  │  │
│  │  - Response caching                                 │  │
│  │  - Error recovery                                   │  │
│  └─────────────────────┬───────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────▼───────────────────────────────┐  │
│  │  Transport Layer                                     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │  stdio   │  │   SSE    │  │  HTTP/gRPC       │  │  │
│  │  │(local)   │  │(remote)  │  │  (distributed)   │  │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
              │               │               │
     ┌────────▼─────┐ ┌──────▼──────┐ ┌──────▼──────┐
     │ MCP Server 1 │ │ MCP Server 2│ │ MCP Server N│
     │ (Browser)    │ │ (Code Exec) │ │ (Composio)  │
     └──────────────┘ └─────────────┘ └─────────────┘
```

### 3.2 MCP Server Registration

```python
class MCPServerConfig(BaseModel):
    """Configuration for an MCP server"""
    server_id: str
    name: str
    description: str

    # Transport
    transport: Literal["stdio", "sse", "http", "grpc"]
    command: Optional[str] = None     # For stdio
    args: Optional[list[str]] = None  # For stdio
    url: Optional[str] = None         # For SSE/HTTP/gRPC
    env: dict[str, str] = Field(default_factory=dict)

    # Capabilities
    tools: list[str]                  # Tool names this server provides
    resources: list[str] = Field(default_factory=list)
    prompts: list[str] = Field(default_factory=list)

    # Lifecycle
    auto_start: bool = True
    restart_on_failure: bool = True
    max_restart_attempts: int = 3
    health_check_interval_seconds: int = 30

    # Security
    required_permissions: list[str] = Field(default_factory=list)
    allowed_agents: list[str] = []    # Empty = all agents
    denied_agents: list[str] = []
    rate_limit_per_minute: int = 60

    # Metadata
    source_repo: str
    priority: Literal["P0", "P1", "P2", "P3"]
    version: str
```

### 3.3 Tool Call Flow

```
Agent                    MCP Client                 MCP Server
  │                          │                          │
  │── 1. tool_call ─────────►│                          │
  │   (name, args)           │                          │
  │                          │── 2. permission_check    │
  │                          │── 3. rate_limit_check    │
  │                          │── 4. schema_validate     │
  │                          │                          │
  │                          │── 5. call_tool ─────────►│
  │                          │   (MCP protocol)         │
  │                          │                          │── 6. execute
  │                          │                          │── 7. result
  │                          │◄── 8. tool_result ───────│
  │                          │                          │
  │                          │── 9. validate_result     │
  │                          │── 10. audit_log          │
  │◄── 11. result ──────────│                          │
  │                          │                          │
```

---

## 4. Complete Tool Catalog

### 4.1 Browser Tools (Source: CloakBrowser)

| Tool Name | Capability | Input Schema | Output Schema | Priority |
|---|---|---|---|---|
| `browser.navigate` | Navigate to URL | `{url: string, waitUntil?: string}` | `{title: string, url: string}` | P1 |
| `browser.click` | Click element | `{selector: string, button?: string}` | `{success: boolean}` | P1 |
| `browser.type` | Type text into element | `{selector: string, text: string, clear?: boolean}` | `{success: boolean}` | P1 |
| `browser.screenshot` | Capture page screenshot | `{selector?: string, fullPage?: boolean}` | `{image: base64, width: int, height: int}` | P1 |
| `browser.extract_text` | Extract page text | `{selector?: string}` | `{text: string}` | P1 |
| `browser.extract_links` | Extract all links | `{selector?: string}` | `{links: [{text, href}]}` | P2 |
| `browser.get_dom` | Get page DOM | `{selector?: string, depth?: int}` | `{html: string}` | P2 |
| `browser.scroll` | Scroll page | `{direction: string, amount: int}` | `{success: boolean}` | P2 |
| `browser.hover` | Hover over element | `{selector: string}` | `{success: boolean}` | P2 |
| `browser.drag` | Drag element | `{from: string, to: string}` | `{success: boolean}` | P3 |
| `browser.wait_for` | Wait for element | `{selector: string, timeout?: int}` | `{found: boolean}` | P1 |
| `browser.cookies_get` | Get cookies | `{domain?: string}` | `{cookies: [...]}` | P2 |
| `browser.cookies_set` | Set cookie | `{name: string, value: string, domain: string}` | `{success: boolean}` | P2 |
| `browser.local_storage` | Access local storage | `{action: string, key: string, value?: string}` | `{value?: string}` | P3 |
| `browser.proxy_set` | Set proxy | `{host: string, port: int, auth?: string}` | `{success: boolean}` | P2 |
| `browser.ua_set` | Set user agent | `{userAgent: string}` | `{success: boolean}` | P2 |
| `browser.fingerprint_mask` | Mask browser fingerprint | `{profile?: string}` | `{success: boolean}` | P1 |
| `browser.tab_new` | Open new tab | `{url?: string}` | `{tabId: string}` | P2 |
| `browser.tab_switch` | Switch tab | `{tabId: string}` | `{success: boolean}` | P2 |
| `browser.tab_close` | Close tab | `{tabId: string}` | `{success: boolean}` | P3 |
| `browser.pdf_save` | Save page as PDF | `{path: string, format?: string}` | `{path: string}` | P3 |
| `browser.intercept` | Intercept network requests | `{pattern: string, action: string}` | `{interceptId: string}` | P2 |

**CloakBrowser specifics**: 58 C++ patches to Chromium providing anti-detection,
canvas/WebGL fingerprint masking, timezone spoofing, WebRTC leak prevention,
and navigator property masking. All tools inherit stealth capabilities by default.

### 4.2 Computer-Use Tools (Source: open-computer-use)

| Tool Name | Capability | Input Schema | Output Schema | Priority |
|---|---|---|---|---|
| `computer.screen_capture` | Capture screen | `{display?: int, region?: {x,y,w,h}}` | `{image: base64, width: int, height: int}` | P2 |
| `computer.mouse_click` | Click at coordinates | `{x: int, y: int, button?: string, clicks?: int}` | `{success: boolean}` | P2 |
| `computer.mouse_drag` | Drag from A to B | `{fromX: int, fromY: int, toX: int, toY: int}` | `{success: boolean}` | P2 |
| `computer.mouse_scroll` | Scroll at position | `{x: int, y: int, direction: string, amount: int}` | `{success: boolean}` | P2 |
| `computer.keyboard_type` | Type text | `{text: string}` | `{success: boolean}` | P2 |
| `computer.keyboard_hotkey` | Press key combo | `{keys: [string]}` | `{success: boolean}` | P2 |
| `computer.keyboard_paste` | Paste clipboard | `{text: string}` | `{success: boolean}` | P2 |
| `computer.window_list` | List windows | `{}` | `{windows: [{id, title, app}]}` | P3 |
| `computer.window_focus` | Focus window | `{windowId: string}` | `{success: boolean}` | P3 |
| `computer.window_resize` | Resize window | `{windowId: string, width: int, height: int}` | `{success: boolean}` | P3 |
| `computer.app_launch` | Launch application | `{appName: string, args?: string}` | `{processId: int}` | P3 |
| `computer.app_quit` | Quit application | `{processId: int}` | `{success: boolean}` | P3 |

### 4.3 API Tools (Source: Composio + public-apis)

#### Composio Integration (250+ tools)

Composio provides pre-built integrations for external services. Each integration
is wrapped as an MCP tool with standardized input/output schemas.

**Categories and key integrations:**

| Category | Key Integrations | Tool Count | Priority |
|---|---|---|---|
| **Productivity** | Google Workspace, Notion, Slack, Trello | 35+ | P1 |
| **Development** | GitHub, GitLab, Jira, Linear | 25+ | P1 |
| **Communication** | Gmail, Outlook, SendGrid, Twilio | 20+ | P1 |
| **Cloud** | AWS, GCP, Azure, Vercel, Netlify | 30+ | P2 |
| **Database** | PostgreSQL, MongoDB, Redis, Supabase | 15+ | P1 |
| **Finance** | Stripe, Plaid, QuickBooks | 10+ | P2 |
| **Social** | Twitter/X, LinkedIn, Reddit | 10+ | P2 |
| **AI/ML** | OpenAI, Anthropic, Hugging Face | 15+ | P1 |
| **Storage** | S3, Cloudflare R2, Dropbox | 10+ | P2 |
| **Monitoring** | Datadog, PagerDuty, Sentry | 10+ | P2 |
| **CRM** | Salesforce, HubSpot, Pipedrive | 8+ | P3 |
| **E-commerce** | Shopify, WooCommerce | 5+ | P3 |
| **Other** | Various niche services | 70+ | P3 |

**Composio MCP tool naming convention:**
```
composio.<service>.<action>

Examples:
  composio.github.create_pull_request
  composio.slack.send_message
  composio.stripe.create_payment
  composio.notion.create_page
  composio.aws.list_ec2_instances
```

#### public-apis Catalog (1400+ APIs)

The public-apis repository provides a curated list of free and paid APIs. These
are not pre-integrated; they serve as a reference catalog for tool discovery.

**Integration strategy:**
1. Index all 1400+ APIs in the knowledge base (Qdrant)
2. When an agent needs an API not in Composio, search the catalog
3. Auto-generate MCP tool wrapper from OpenAPI spec if available
4. Fall back to generic REST tool with manual configuration

```python
class PublicAPICatalog:
    """Indexes public-apis for tool discovery"""

    async def search(self, query: str, category: str = None) -> list[APIEntry]:
        """Search for APIs by capability"""
        ...

    async def generate_mcp_wrapper(self, api_entry: APIEntry) -> MCPServerConfig:
        """Auto-generate MCP server from API spec"""
        ...

    async def get_openapi_spec(self, api_url: str) -> dict:
        """Fetch and parse OpenAPI specification"""
        ...
```

### 4.4 Data Tools

| Tool Name | Capability | Source Repo | Priority |
|---|---|---|---|
| `data.sql_query` | Execute SQL query | agentcloud | P1 |
| `data.sql_insert` | Insert records | agentcloud | P1 |
| `data.sql_update` | Update records | agentcloud | P1 |
| `data.sql_delete` | Delete records | agentcloud | P1 |
| `data.sql_migrate` | Run migration | New | P2 |
| `data.file_read` | Read file content | MCP Reference | P0 |
| `data.file_write` | Write file content | MCP Reference | P0 |
| `data.file_list` | List directory | MCP Reference | P0 |
| `data.file_search` | Search files (ripgrep) | MCP Reference | P1 |
| `data.file_transform` | Transform file (CSV→JSON, etc) | New | P2 |
| `data.vector_embed` | Generate embeddings | agentcloud (Qdrant) | P1 |
| `data.vector_search` | Semantic search | agentcloud (Qdrant) | P1 |
| `data.vector_upsert` | Upsert vectors | agentcloud (Qdrant) | P1 |
| `data.vector_delete` | Delete from collection | agentcloud (Qdrant) | P2 |
| `data.pipeline_etl` | Extract-transform-load | New | P2 |
| `data.pipeline_validate` | Validate data quality | New | P2 |

### 4.5 Code Execution Tools

| Tool Name | Capability | Source Repo | Priority |
|---|---|---|---|
| `code.run_python` | Execute Python in sandbox | ai-manus, OpenHands | P0 |
| `code.run_javascript` | Execute JS in sandbox | ai-manus | P1 |
| `code.run_shell` | Execute shell command | OpenHands | P1 |
| `code.install_package` | Install Python/JS package | ai-manus | P1 |
| `code.git_clone` | Clone repository | OpenHands | P1 |
| `code.git_commit` | Commit changes | OpenHands | P1 |
| `code.git_diff` | Show diff | OpenHands | P1 |
| `code.git_log` | Show commit log | OpenHands | P2 |
| `code.compile` | Compile code | New | P2 |
| `code.lint` | Run linter | New | P2 |
| `code.format` | Format code | New | P2 |
| `code.test_run` | Run tests | OpenHands | P1 |

### 4.6 Messaging Tools (Source: nanobot, openfang, Composio)

| Tool Name | Capability | Source Repo | Priority |
|---|---|---|---|
| `msg.email_send` | Send email | Composio | P2 |
| `msg.email_read` | Read email | Composio | P2 |
| `msg.slack_send` | Send Slack message | Composio | P2 |
| `msg.slack_read` | Read Slack messages | Composio | P2 |
| `msg.discord_send` | Send Discord message | Composio | P3 |
| `msg.telegram_send` | Send Telegram message | nanobot | P2 |
| `msg.telegram_receive` | Receive Telegram messages | nanobot | P2 |
| `msg.whatsapp_send` | Send WhatsApp message | nanobot | P3 |
| `msg.whatsapp_receive` | Receive WhatsApp messages | nanobot | P3 |
| `msg.webhook_register` | Register webhook | openfang | P2 |
| `msg.webhook_dispatch` | Dispatch webhook | openfang | P2 |
| `msg.push_notify` | Push notification | Composio | P3 |

### 4.7 Infrastructure Tools

| Tool Name | Capability | Source Repo | Priority |
|---|---|---|---|
| `infra.container_run` | Run Docker container | ai-manus | P1 |
| `infra.container_stop` | Stop container | ai-manus | P1 |
| `infra.container_logs` | Get container logs | ai-manus | P1 |
| `infra.container_exec` | Execute in container | ai-manus | P1 |
| `infra.deploy` | Deploy application | openfang | P2 |
| `infra.scale` | Scale deployment | New | P2 |
| `infra.monitor` | Get system metrics | openfang | P1 |
| `infra.dns_lookup` | DNS resolution | public-ip-address | P3 |
| `infra.ip_geolocate` | IP geolocation | public-ip-address | P3 |
| `infra.cred_store` | Store credential | AI-MultiColony | P0 |
| `infra.cred_retrieve` | Retrieve credential | AI-MultiColony | P0 |
| `infra.cred_rotate` | Rotate credential | AI-MultiColony | P1 |

---

## 5. CloakBrowser Integration Plan

### 5.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  CloakBrowser MCP Server                 │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ MCP Handler │  │ Session Mgr  │  │ Stealth Mgr   │  │
│  │ (tool calls)│  │ (browser ctx)│  │ (fingerprint) │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                │                   │          │
│  ┌──────▼────────────────▼───────────────────▼───────┐  │
│  │              Playwright Core                       │  │
│  │          (with CloakBrowser patches)               │  │
│  └───────────────────────┬───────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼───────────────────────────┐  │
│  │          Chromium (Patched)                        │  │
│  │  - Canvas fingerprint masking                      │  │
│  │  - WebGL renderer spoofing                        │  │
│  │  - Navigator property masking                     │  │
│  │  - Timezone spoofing                              │  │
│  │  - WebRTC leak prevention                         │  │
│  │  - Audio context fingerprint masking              │  │
│  │  - Font enumeration masking                       │  │
│  │  - Screen resolution spoofing                     │  │
│  │  - Plugin/MIME type masking                       │  │
│  │  - Battery API masking                            │  │
│  │  - Hardware concurrency spoofing                  │  │
│  │  - ... (58 patches total)                         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Integration Steps

| Step | Task | Effort | Dependency |
|---|---|---|---|
| 1 | Build CloakBrowser Chromium from source with 58 patches | 2 days | Chromium build toolchain |
| 2 | Create Python MCP server wrapping Playwright + CloakBrowser | 3 days | MCP SDK |
| 3 | Implement session management (isolated contexts per agent) | 2 days | Redis |
| 4 | Add stealth profile management (preset fingerprint profiles) | 1 day | None |
| 5 | Integrate with MCP client pool (connection management) | 1 day | MCP client |
| 6 | Write tool permission policies (which agents get browser) | 1 day | Security model |
| 7 | Integration testing with research agents | 2 days | Research agents |
| 8 | Load testing (concurrent browser sessions) | 1 day | Test infra |

### 5.3 Session Isolation

```python
class BrowserSessionConfig(BaseModel):
    """Per-agent browser session configuration"""
    session_id: str
    agent_id: str
    colony_id: str

    # Isolation
    isolated_context: bool = True      # Fresh browser context per session
    clear_on_close: bool = True        # Clear cookies/storage on session end
    proxy_per_session: bool = False    # Unique proxy per session

    # Stealth
    stealth_profile: str = "default"   # Fingerprint profile name
    mask_canvas: bool = True
    mask_webgl: bool = True
    mask_navigator: bool = True
    mask_timezone: bool = True
    prevent_webrtc_leak: bool = True

    # Resources
    max_pages: int = 5                 # Max tabs per session
    max_memory_mb: int = 512           # Memory limit
    timeout_seconds: int = 300         # Page load timeout
    idle_timeout_seconds: int = 600    # Session idle timeout
```

---

## 6. open-computer-use Integration Plan

### 6.1 Architecture

```
┌──────────────────────────────────────────────────┐
│           open-computer-use MCP Server            │
│                                                  │
│  ┌─────────────┐  ┌──────────────┐              │
│  │ MCP Handler │  │ Display Mgr  │              │
│  │ (tool calls)│  │ (multi-mon)  │              │
│  └──────┬──────┘  └──────┬───────┘              │
│         │                │                       │
│  ┌──────▼────────────────▼───────┐              │
│  │  Screen Capture (Swift)       │              │
│  │  - CGWindowListCreateImage    │              │
│  │  - Region capture             │              │
│  │  - Display selection          │              │
│  └──────────────┬────────────────┘              │
│                 │                                │
│  ┌──────────────▼────────────────┐              │
│  │  Input Simulation (Go)        │              │
│  │  - CGEvent (mouse/keyboard)   │              │
│  │  - Accessibility API          │              │
│  │  - AppleScript bridge         │              │
│  └──────────────┬────────────────┘              │
│                 │                                │
│  ┌──────────────▼────────────────┐              │
│  │  MCP Server (TypeScript)      │              │
│  │  - Tool registration          │              │
│  │  - Schema validation          │              │
│  │  - Permission gating          │              │
│  └───────────────────────────────┘              │
└──────────────────────────────────────────────────┘

Platform support:
  macOS: Full support (Swift + Go + Accessibility)
  Linux: Partial support (xdotool + scrot, no accessibility)
  Windows: Planned (pyautogui + Win32 API)
```

### 6.2 Integration Steps

| Step | Task | Effort | Dependency |
|---|---|---|---|
| 1 | Build Swift screen capture module | 2 days | macOS dev environment |
| 2 | Build Go input simulation module | 2 days | Go toolchain |
| 3 | Create TypeScript MCP server | 3 days | MCP TypeScript SDK |
| 4 | Add multi-display support | 1 day | Display API |
| 5 | Implement safety guardrails (confirmation for destructive actions) | 2 days | Security model |
| 6 | Add accessibility tree extraction | 3 days | macOS Accessibility API |
| 7 | Integrate with MCP client pool | 1 day | MCP client |
| 8 | Cross-platform testing | 3 days | Linux/Windows test envs |

### 6.3 Safety Constraints

```python
COMPUTER_USE_SAFETY = {
    # Actions requiring human confirmation
    "require_confirmation": [
        "computer.app_quit",        # Never quit apps without confirmation
        "computer.keyboard_hotkey",  # System shortcuts could be destructive
        "computer.window_close",     # Could lose unsaved work
    ],

    # Rate limits (prevent rapid clicking/typing)
    "rate_limits": {
        "clicks_per_second": 5,
        "keys_per_second": 20,
        "actions_per_minute": 60,
    },

    # Excluded applications (never interact with these)
    "excluded_apps": [
        "Keychain Access",       # Security
        "System Preferences",    # System config
        "Activity Monitor",      # Could kill processes
        "Terminal (root)",       # Root terminal sessions
    ],

    # Screenshot privacy
    "privacy": {
        "mask_sensitive_regions": True,  # Mask password fields in screenshots
        "redact_pii": True,             # Redact PII from OCR results
        "no_persistent_screenshots": True,  # Don't save screenshots to disk
    },
}
```

---

## 7. Composio 250+ Tools Integration

### 7.1 Integration Architecture

```
┌─────────────────────────────────────────────┐
│            Composio MCP Gateway              │
│                                             │
│  ┌──────────────┐   ┌──────────────────┐   │
│  │ Auth Manager │   │ Tool Router      │   │
│  │ (OAuth, API  │   │ (route to right  │   │
│  │  keys, etc.) │   │  Composio tool)  │   │
│  └──────┬───────┘   └────────┬─────────┘   │
│         │                    │              │
│  ┌──────▼────────────────────▼───────────┐  │
│  │         Composio SDK (Python)         │  │
│  │  - 250+ pre-built integrations        │  │
│  │  - OAuth flow management              │  │
│  │  - Rate limiting per service          │  │
│  │  - Error handling & retries           │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 7.2 Authentication Flow

```python
class ComposioAuthManager:
    """
    Manages authentication for Composio-integrated services.
    Each colony gets its own auth context to prevent credential leakage.
    """

    async def authenticate(self, colony_id: str, service: str) -> str:
        """Get authenticated client for a service"""
        # 1. Check colony credential store
        creds = await self.credential_store.retrieve(colony_id, f"composio.{service}")

        # 2. If no creds, initiate OAuth flow
        if not creds:
            if service in OAUTH_SERVICES:
                auth_url = await self.initiate_oauth(colony_id, service)
                return auth_url  # Return URL for human approval
            else:
                raise CredentialNotFoundError(service)

        # 3. Validate and return client
        client = composio.Client(creds.access_token)
        return client

    async def initiate_oauth(self, colony_id: str, service: str) -> str:
        """Initiate OAuth flow for a service"""
        ...

    async def revoke(self, colony_id: str, service: str) -> None:
        """Revoke access for a service"""
        ...
```

### 7.3 Tool Discovery and Registration

```python
async def register_composio_tools():
    """
    Auto-discover and register all Composio tools as MCP tools.
    This runs at startup and on schedule.
    """
    composio_client = composio.Client()

    # Get all available tools
    tools = composio_client.get_all_tools()

    for tool in tools:
        # Convert Composio tool schema to MCP tool schema
        mcp_tool = convert_to_mcp_tool(tool)

        # Determine priority based on category
        priority = COMPOSIO_CATEGORY_PRIORITY.get(tool.category, "P3")

        # Register with MCP server registry
        await mcp_registry.register(
            MCPServerConfig(
                server_id=f"composio.{tool.service}",
                name=f"Composio {tool.service}",
                transport="sse",
                url="http://composio-gateway:3001/mcp",
                tools=[mcp_tool.name],
                required_permissions=[f"composio.{tool.service}"],
                source_repo="Composio (external)",
                priority=priority,
                version=tool.version,
            )
        )
```

---

## 8. public-apis Catalog Integration

### 8.1 Integration Strategy

The public-apis repository is not a tool itself but a reference catalog. Integration
involves indexing it into the knowledge base for tool discovery.

```python
class PublicAPIsIndexer:
    """
    Indexes the public-apis catalog into Qdrant for semantic search.
    When an agent needs a capability not in the active tool registry,
    it can search this catalog to find relevant APIs.
    """

    async def index_catalog(self, catalog_path: str) -> int:
        """
        Index all APIs from the public-apis catalog.
        Returns: number of APIs indexed
        """
        apis = self.parse_catalog(catalog_path)
        count = 0
        for api in apis:
            # Generate embedding for API description
            embedding = await self.embed(api.description + " " + api.category)

            # Store in Qdrant
            await self.qdrant.upsert(
                collection="public_apis",
                point_id=api.name,
                vector=embedding,
                payload={
                    "name": api.name,
                    "description": api.description,
                    "category": api.category,
                    "auth_type": api.auth,
                    "https": api.https,
                    "cors": api.cors,
                    "base_url": api.base_url,
                    "docs_url": api.docs_url,
                }
            )
            count += 1
        return count

    async def search(self, query: str, category: str = None) -> list[dict]:
        """Search for APIs by capability description"""
        embedding = await self.embed(query)
        results = await self.qdrant.search(
            collection="public_apis",
            query_vector=embedding,
            filter={"category": category} if category else None,
            limit=10,
        )
        return results

    async def generate_wrapper(self, api_name: str) -> Optional[MCPServerConfig]:
        """Attempt to auto-generate MCP wrapper from API spec"""
        api = await self.get_api(api_name)
        openapi_spec = await self.fetch_openapi_spec(api.docs_url)

        if openapi_spec:
            return self.spec_to_mcp_config(api, openapi_spec)
        return None
```

### 8.2 Catalog Statistics

| Category | API Count | Auth Required | HTTPS | CORS Enabled |
|---|---|---|---|---|
| Animals | 25+ | Mixed | Most | Varies |
| Anime | 10+ | Low | Most | Varies |
| Anti-Malware | 5+ | High | All | Limited |
| Art & Design | 15+ | Mixed | Most | Varies |
| Authentication | 10+ | High | All | Good |
| Blockchain | 20+ | Mixed | Most | Limited |
| Books | 15+ | Low | Most | Good |
| Business | 20+ | High | All | Limited |
| Calendar | 10+ | Mixed | All | Good |
| Cloud | 30+ | High | All | Limited |
| ... | ... | ... | ... | ... |
| **Total** | **1400+** | Varies | Most | Varies |

---

## 9. Tool Safety and Permission Model

### 9.1 Permission Levels

```python
class ToolPermission(str, Enum):
    DENIED = "denied"            # Cannot use this tool
    READ_ONLY = "read_only"      # Can read, cannot modify
    WRITE = "write"              # Can create and modify
    ADMIN = "admin"              # Full access including delete

class ToolSafetyPolicy(BaseModel):
    """Safety policy for a tool, scoped to agent+colony"""
    tool_name: str
    agent_type: str              # Agent type this policy applies to
    colony_type: str             # Colony type this policy applies to

    permission: ToolPermission

    # Constraints
    max_calls_per_minute: int = 30
    max_calls_per_hour: int = 500
    max_payload_size_kb: int = 1024

    # Approval requirements
    requires_approval: bool = False       # Human approval needed
    approval_timeout_seconds: int = 300   # Timeout for approval

    # Data constraints
    prevent_pii: bool = True              # Scan for PII in tool inputs
    prevent_secrets: bool = True          # Scan for secrets in tool outputs
    audit_all_calls: bool = False         # Log every call (for sensitive tools)
```

### 9.2 Default Permission Matrix

| Tool Category | Coding Agent | Research Agent | Trading Agent | Ops Agent | Creative Agent |
|---|---|---|---|---|---|
| Browser (nav) | WRITE | WRITE | READ_ONLY | READ_ONLY | WRITE |
| Browser (stealth) | DENIED | WRITE | DENIED | DENIED | READ_ONLY |
| Computer-use | DENIED | DENIED | DENIED | WRITE | DENIED |
| API (read) | READ_ONLY | WRITE | WRITE | READ_ONLY | READ_ONLY |
| API (write) | DENIED | DENIED | WRITE | DENIED | DENIED |
| Data (read) | READ_ONLY | READ_ONLY | READ_ONLY | READ_ONLY | READ_ONLY |
| Data (write) | WRITE | DENIED | WRITE | WRITE | DENIED |
| Code execution | ADMIN | READ_ONLY | DENIED | ADMIN | READ_ONLY |
| Messaging | DENIED | READ_ONLY | DENIED | WRITE | DENIED |
| Infrastructure | READ_ONLY | DENIED | DENIED | ADMIN | DENIED |
| Credentials | READ_ONLY | DENIED | READ_ONLY | ADMIN | DENIED |

### 9.3 PII and Secret Scanning

```python
class ToolCallScanner:
    """
    Scans tool call inputs and outputs for PII and secrets.
    Blocks or redacts as configured.
    """

    PII_PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "api_key": r"\b(sk|pk|api_key|token|secret)[_-][a-zA-Z0-9]{20,}\b",
    }

    async def scan_input(self, tool_name: str, args: dict) -> ScanResult:
        """Scan tool input for PII/secrets before execution"""
        ...

    async def scan_output(self, tool_name: str, result: dict) -> ScanResult:
        """Scan tool output for PII/secrets before returning to agent"""
        ...
```

### 9.4 Audit Logging

```python
class ToolAuditLog:
    """
    Comprehensive audit trail for all tool usage.
    Required for compliance and debugging.
    """

    async def log(self, entry: ToolAuditEntry) -> None:
        """
        Log a tool usage event.
        Stored in PostgreSQL, retained for 90 days.
        """
        ...

class ToolAuditEntry(BaseModel):
    timestamp: datetime
    agent_id: str
    colony_id: str
    tool_name: str
    action: str
    input_hash: str          # SHA-256 hash of input (not full input)
    output_hash: str         # SHA-256 hash of output
    duration_ms: int
    success: bool
    error: Optional[str]
    pii_detected: bool
    secrets_detected: bool
    token_cost: Optional[float]
```

---

## 10. Tool Implementation Priority

### 10.1 Phase 1: Foundation (Weeks 1-4)

| Tool | Priority | Source | Effort |
|---|---|---|---|
| Filesystem (read/write/list) | P0 | MCP Reference | 1 day |
| Code execution (Python sandbox) | P0 | ai-manus + OpenHands | 3 days |
| Credential store/retrieve | P0 | AI-MultiColony | 2 days |
| Shell execution (sandboxed) | P0 | OpenHands | 2 days |
| MCP client infrastructure | P0 | New | 5 days |

### 10.2 Phase 2: Core (Weeks 5-8)

| Tool | Priority | Source | Effort |
|---|---|---|---|
| Browser (navigate/click/type) | P1 | CloakBrowser | 5 days |
| Browser (stealth features) | P1 | CloakBrowser | 3 days |
| SQL query | P1 | agentcloud | 2 days |
| Vector search | P1 | agentcloud (Qdrant) | 2 days |
| Composio gateway (top 50 tools) | P1 | Composio | 3 days |
| Git operations | P1 | OpenHands | 2 days |
| Browser (screenshot/extract) | P1 | CloakBrowser | 2 days |

### 10.3 Phase 3: Extended (Weeks 9-12)

| Tool | Priority | Source | Effort |
|---|---|---|---|
| Computer-use (screen/mouse/keyboard) | P2 | open-computer-use | 7 days |
| Messaging (Slack/Telegram) | P2 | nanobot + Composio | 3 days |
| public-apis catalog indexer | P2 | public-apis | 3 days |
| Composio gateway (all 250+ tools) | P2 | Composio | 5 days |
| Container management | P2 | ai-manus | 3 days |
| IP geolocation | P3 | public-ip-address | 1 day |

### 10.4 Phase 4: Advanced (Weeks 13-16)

| Tool | Priority | Source | Effort |
|---|---|---|---|
| Computer-use (accessibility) | P3 | open-computer-use | 5 days |
| API auto-wrapper generation | P3 | public-apis + OpenAPI | 5 days |
| Webhook system | P3 | openfang | 3 days |
| Advanced browser (intercept, PDF) | P3 | CloakBrowser | 3 days |
| Data pipeline tools | P2 | New | 5 days |

---

## 11. Tool Performance Requirements

| Tool Category | P50 Latency | P99 Latency | Throughput | Max Concurrent |
|---|---|---|---|---|
| Filesystem | 10ms | 50ms | 1000/s | 100 |
| Code execution | 2s | 10s | 10/s | 20 |
| Browser (navigate) | 2s | 8s | 5/s | 10 |
| Browser (interact) | 500ms | 2s | 20/s | 10 |
| SQL query | 100ms | 1s | 50/s | 30 |
| Vector search | 50ms | 200ms | 100/s | 50 |
| API call (external) | 500ms | 5s | 30/s | 50 |
| Computer-use | 100ms | 500ms | 30/s | 5 |
| Composio (proxied) | 1s | 5s | 20/s | 30 |

---

## Appendix A: MCP Server Configuration Reference

```yaml
# config/mcp_servers.yaml
servers:
  filesystem:
    transport: stdio
    command: npx
    args: ["@modelcontextprotocol/server-filesystem", "/workspace"]
    priority: P0
    auto_start: true

  code_execution:
    transport: stdio
    command: python
    args: ["-m", "mcp_code_server"]
    env:
      SANDBOX: e2b
      TIMEOUT: "60"
    priority: P0
    auto_start: true

  browser:
    transport: stdio
    command: python
    args: ["-m", "mcp_browser_server"]
    env:
      BROWSER_ENGINE: cloak
      HEADLESS: "true"
      STEALTH_PROFILE: default
    priority: P1
    auto_start: true
    max_instances: 5

  computer_use:
    transport: stdio
    command: node
    args: ["mcp-computer-use-server.js"]
    priority: P2
    auto_start: false  # Only start when needed
    allowed_agents: ["sp.computer_use", "ops.*"]

  composio:
    transport: sse
    url: http://composio-gateway:3001/mcp
    priority: P1
    auto_start: true

  qdrant:
    transport: stdio
    command: python
    args: ["-m", "mcp_qdrant_server"]
    env:
      QDRANT_URL: http://qdrant:6333
    priority: P1
    auto_start: true

  credentials:
    transport: stdio
    command: python
    args: ["-m", "mcp_credential_server"]
    env:
      ENCRYPTION_KEY: ${VAULT_KEY}
    priority: P0
    auto_start: true
    audit_all_calls: true
```

## Appendix B: Tool Health Check Protocol

```python
class ToolHealthChecker:
    """
    Periodic health checking for all MCP servers.
    Unhealthy servers are automatically restarted.
    """

    async def check_health(self, server: MCPServerConfig) -> HealthStatus:
        """
        Health check sequence:
        1. Ping the MCP server (list_tools with limit=0)
        2. Measure response time
        3. Verify tool schemas haven't changed
        4. Check resource usage (memory, CPU)
        """
        ...

    async def on_unhealthy(self, server: MCPServerConfig, status: HealthStatus):
        """
        Recovery sequence:
        1. Log unhealthy state
        2. Attempt graceful restart
        3. If restart fails, mark as unavailable
        4. Route traffic to fallback if available
        5. Alert operations team if critical (P0/P1)
        """
        ...
```
