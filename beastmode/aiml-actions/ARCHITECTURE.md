# AIML Actions Architecture

## Overview

**AIML Actions** is a hybrid system that combines AIML (Artificial Intelligence Markup Language) pattern matching with LLM capabilities and GitHub Actions workflows. It creates a "Choose Your Own Adventure" style interface for DevOps orchestration.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│                    "create 3 tenants"                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AIML PATTERN MATCHER                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ <pattern>CREATE * TENANTS</pattern>                      │   │
│  │ <template>                                               │   │
│  │   <action workflow="create-tenants" count="<star/>"/>    │   │
│  │ </template>                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
           │                                    │
           │ MATCH                              │ NO MATCH
           ▼                                    ▼
┌──────────────────────┐            ┌──────────────────────┐
│   GITHUB ACTIONS     │            │    LLM FALLBACK      │
│   WORKFLOW DISPATCH  │            │  (SmolLM2 / OpenAI)  │
└──────────────────────┘            └──────────────────────┘
           │                                    │
           ▼                                    ▼
┌──────────────────────┐            ┌──────────────────────┐
│   EXECUTE WORKFLOW   │            │  GENERATE RESPONSE   │
│   create-tenants.yml │            │  + LEARN NEW PATTERN │
└──────────────────────┘            └──────────────────────┘
```

## Core Components

### 1. AIML Pattern Engine

The AIML engine handles structured, predictable operations with deterministic responses.

**Extended AIML Tags for Actions:**

| Tag | Description | Example |
|-----|-------------|---------|
| `<action>` | Trigger a GitHub Action | `<action workflow="deploy"/>` |
| `<choice>` | Present branching options | `<choice id="env">prod\|staging\|dev</choice>` |
| `<confirm>` | Require user confirmation | `<confirm>Deploy to production?</confirm>` |
| `<llm>` | Invoke LLM for dynamic content | `<llm>Explain this error: <star/></llm>` |
| `<learn-action>` | Learn new pattern from interaction | `<learn-action pattern="..." workflow="..."/>` |

### 2. Choose Your Own Adventure Engine

The adventure engine manages branching decision trees for complex workflows.

```yaml
# adventure.yaml
adventure: deploy-application
start: choose-environment

nodes:
  choose-environment:
    prompt: "Where would you like to deploy?"
    choices:
      - label: "Production"
        next: confirm-production
      - label: "Staging"
        next: deploy-staging
      - label: "Development"
        next: deploy-dev

  confirm-production:
    prompt: "⚠️ Production deployment requires approval. Continue?"
    choices:
      - label: "Yes, I have approval"
        action: deploy-prod
        next: deployment-started
      - label: "No, go back"
        next: choose-environment

  deploy-staging:
    action: deploy-staging
    next: deployment-started

  deploy-dev:
    action: deploy-dev
    next: deployment-started

  deployment-started:
    prompt: "Deployment initiated! Track progress?"
    choices:
      - label: "Yes, show logs"
        action: show-logs
      - label: "No, I'm done"
        next: end
```

### 3. LLM Fallback System

When no AIML pattern matches, the LLM provides:
- Novel response generation
- Intent classification
- Pattern suggestion for learning

```python
class LLMFallback:
    def handle_unmatched(self, input: str) -> Response:
        # 1. Try to classify intent
        intent = self.classify_intent(input)
        
        # 2. If intent maps to known action, suggest pattern
        if intent in self.known_intents:
            return self.suggest_pattern(input, intent)
        
        # 3. Otherwise, generate creative response
        return self.generate_response(input)
    
    def suggest_pattern(self, input: str, intent: str) -> Response:
        # Propose new AIML pattern for user approval
        pattern = self.generalize_pattern(input)
        return Response(
            text=f"I can learn this! Should I add:\n<pattern>{pattern}</pattern>",
            action="learn",
            data={"pattern": pattern, "intent": intent}
        )
```

### 4. GitHub Actions Integration

Each AIML pattern can map to a GitHub Actions workflow:

```xml
<category>
  <pattern>CREATE * USERS IN * ORG</pattern>
  <template>
    <action 
      workflow="create-users"
      inputs='{"count": "<star index="1"/>", "org": "<star index="2"/>"}'
    />
    Creating <star index="1"/> users in <star index="2"/> organization...
  </template>
</category>
```

Generated workflow dispatch:

```yaml
# .github/workflows/create-users.yml
name: Create Users
on:
  workflow_dispatch:
    inputs:
      count:
        description: 'Number of users to create'
        required: true
        type: number
      org:
        description: 'Organization name'
        required: true
        type: string

jobs:
  create-users:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create Users
        run: |
          python god-mode/scripts/rapid_provision.py \
            --action create-users \
            --count ${{ inputs.count }} \
            --org ${{ inputs.org }}
```

## Pattern Categories

### 1. Azure AD Operations

```xml
<topic name="AZURE">
  <category>
    <pattern>CREATE TENANT *</pattern>
    <template>
      <action workflow="azure-create-tenant" inputs='{"name": "<star/>"}'/>
    </template>
  </category>
  
  <category>
    <pattern>CREATE * USERS</pattern>
    <template>
      <choice id="user-type">
        What type of users?
        <option value="member">Member users</option>
        <option value="guest">Guest users</option>
        <option value="admin">Admin users</option>
      </choice>
    </template>
  </category>
  
  <category>
    <pattern>SYNC * TO GITHUB</pattern>
    <template>
      <action workflow="sync-azure-github" inputs='{"resource": "<star/>"}'/>
    </template>
  </category>
</topic>
```

### 2. GitHub Operations

```xml
<topic name="GITHUB">
  <category>
    <pattern>CREATE REPO *</pattern>
    <template>
      <action workflow="github-create-repo" inputs='{"name": "<star/>"}'/>
    </template>
  </category>
  
  <category>
    <pattern>CREATE * REPOS FOR *</pattern>
    <template>
      <action workflow="github-bulk-repos" inputs='{"count": "<star index="1"/>", "org": "<star index="2"/>"}'/>
    </template>
  </category>
</topic>
```

### 3. Infrastructure Provisioning

```xml
<topic name="INFRA">
  <category>
    <pattern>DEPLOY * TENANTS WITH * ORGS AND * USERS</pattern>
    <template>
      <confirm>
        This will create:
        - <star index="1"/> Azure AD tenants
        - <star index="2"/> organizations per tenant
        - <star index="3"/> users per organization
        
        Total: <star index="1"/> × <star index="2"/> × <star index="3"/> = 
        <compute><star index="1"/> * <star index="2"/> * <star index="3"/></compute> users
        
        Proceed?
      </confirm>
      <action workflow="mass-provision" inputs='{
        "tenants": "<star index="1"/>",
        "orgs": "<star index="2"/>",
        "users": "<star index="3"/>"
      }'/>
    </template>
  </category>
</topic>
```

## Adventure Scenarios

### Scenario 1: New Project Setup

```
YOU: "I want to start a new project"

BOT: "Great! Let's set up your project. What type?"
     [A] Web Application
     [B] API Service  
     [C] Infrastructure

YOU: "A"

BOT: "Web Application selected. Choose your stack:"
     [A] React + Node.js
     [B] Vue + Python
     [C] Custom

YOU: "A"

BOT: "Perfect! I'll create:
     - GitHub repo with React template
     - Azure AD app registration
     - CI/CD pipeline
     
     What should I name it?"

YOU: "my-awesome-app"

BOT: "Creating my-awesome-app... [Workflow Triggered]
     Track progress: https://github.com/orgitcog/my-awesome-app/actions"
```

### Scenario 2: Emergency Response

```
YOU: "production is down"

BOT: "🚨 INCIDENT MODE ACTIVATED
     
     Running diagnostics...
     [Action: health-check triggered]
     
     While I check, what symptoms are you seeing?"
     [A] 500 errors
     [B] Timeouts
     [C] Authentication failures
     [D] Other

YOU: "A"

BOT: "500 errors detected. Checking recent deployments...
     
     Found: Deploy #142 (2 hours ago) by @dev-user
     
     Options:"
     [A] Rollback to previous version
     [B] View error logs
     [C] Contact on-call engineer
     [D] Scale up resources

YOU: "A"

BOT: "⚠️ CONFIRM: Rollback production to Deploy #141?
     This will affect all users."
     [YES] [NO]

YOU: "YES"

BOT: "Rollback initiated. ETA: 3 minutes.
     [Action: rollback-production triggered]
     
     I'll notify the team and update the status page."
```

## File Structure

```
beastmode/aiml-actions/
├── ARCHITECTURE.md          # This file
├── engine/
│   ├── __init__.py
│   ├── aiml_engine.py       # Core AIML interpreter
│   ├── adventure_engine.py  # Choose Your Own Adventure
│   ├── llm_fallback.py      # LLM integration
│   └── action_dispatcher.py # GitHub Actions dispatcher
├── patterns/
│   ├── azure.aiml           # Azure AD patterns
│   ├── github.aiml          # GitHub patterns
│   ├── infra.aiml           # Infrastructure patterns
│   └── learned.aiml         # Dynamically learned patterns
├── adventures/
│   ├── new-project.yaml     # New project setup
│   ├── incident.yaml        # Incident response
│   └── onboarding.yaml      # User onboarding
├── workflows/
│   ├── azure-create-tenant.yml
│   ├── github-create-repo.yml
│   ├── mass-provision.yml
│   └── ...
└── cli.py                   # Main CLI entry point
```

## Integration Points

### With GodChat

AIML Actions integrates seamlessly with GodChat:

```python
# In godchat.py
from aiml_actions import AIMLEngine, AdventureEngine

class GodChat:
    def __init__(self):
        self.aiml = AIMLEngine()
        self.adventure = AdventureEngine()
        self.llm = LLMClient()
    
    def process(self, input: str) -> str:
        # Check if in adventure mode
        if self.adventure.active:
            return self.adventure.process_choice(input)
        
        # Try AIML pattern match
        response = self.aiml.respond(input)
        if response:
            return response
        
        # Fall back to LLM
        return self.llm.generate(input)
```

### With Local LLM (SmolLM2)

The LLM fallback can use the local SmolLM2 model:

```python
class LLMFallback:
    def __init__(self):
        self.local_url = "http://localhost:8080/v1/chat/completions"
        self.cloud_url = "https://api.openai.com/v1/chat/completions"
    
    def generate(self, prompt: str) -> str:
        # Try local first
        try:
            return self._call_api(self.local_url, prompt)
        except:
            # Fall back to cloud
            return self._call_api(self.cloud_url, prompt)
```

## Learning System

The system can learn new patterns from successful interactions:

```xml
<!-- learned.aiml - Auto-generated -->
<category>
  <pattern>SPIN UP * INSTANCES</pattern>
  <template>
    <!-- Learned from user interaction on 2026-01-11 -->
    <action workflow="scale-instances" inputs='{"count": "<star/>"}'/>
    Scaling to <star/> instances...
  </template>
</category>
```

Learning workflow:
1. User input doesn't match any pattern
2. LLM generates response and identifies intent
3. System proposes pattern generalization
4. User approves → pattern added to `learned.aiml`
5. Pattern available for future use

## Security Considerations

- **Confirmation Required**: Destructive actions require explicit confirmation
- **Audit Logging**: All actions logged with user, timestamp, and inputs
- **Secret Management**: Credentials stored in GitHub Secrets, never in patterns
- **Rate Limiting**: Prevent abuse of automated workflows
- **Role-Based Access**: Different patterns available based on user role
