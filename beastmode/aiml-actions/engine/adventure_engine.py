#!/usr/bin/env python3
"""
Adventure Engine - Choose Your Own Adventure Workflow Orchestration

Manages branching decision trees for complex DevOps workflows,
allowing users to navigate through choices like a CYOA book.
"""

import yaml
import json
import os
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Choice:
    """A choice option in an adventure node"""
    label: str
    next: Optional[str] = None
    action: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    condition: Optional[str] = None


@dataclass
class AdventureNode:
    """A node in the adventure tree"""
    id: str
    prompt: str
    choices: List[Choice] = field(default_factory=list)
    action: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    next: Optional[str] = None
    is_end: bool = False


@dataclass
class AdventureState:
    """Current state of an adventure"""
    adventure_id: str
    current_node: str
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    actions_triggered: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AdventureResponse:
    """Response from processing an adventure step"""
    text: str
    choices: Optional[List[Dict[str, str]]] = None
    action: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    is_end: bool = False
    adventure_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ADVENTURE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AdventureEngine:
    """
    Choose Your Own Adventure Engine for DevOps workflows.
    
    Loads adventure definitions from YAML files and manages
    user navigation through branching decision trees.
    """
    
    def __init__(self, adventures_dir: Optional[str] = None):
        self.adventures: Dict[str, Dict[str, AdventureNode]] = {}
        self.adventure_metadata: Dict[str, Dict[str, Any]] = {}
        self.current_state: Optional[AdventureState] = None
        
        if adventures_dir:
            self.load_adventures(adventures_dir)
    
    @property
    def active(self) -> bool:
        """Check if an adventure is currently active"""
        return self.current_state is not None
    
    def load_adventures(self, adventures_dir: str):
        """Load all adventure YAML files from a directory"""
        path = Path(adventures_dir)
        if not path.exists():
            return
        
        for yaml_file in path.glob("*.yaml"):
            self.load_adventure(str(yaml_file))
        
        for yml_file in path.glob("*.yml"):
            self.load_adventure(str(yml_file))
    
    def load_adventure(self, filepath: str):
        """Load an adventure from a YAML file"""
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            
            adventure_id = data.get("adventure", Path(filepath).stem)
            start_node = data.get("start", "start")
            
            # Store metadata
            self.adventure_metadata[adventure_id] = {
                "name": data.get("name", adventure_id),
                "description": data.get("description", ""),
                "start": start_node,
                "triggers": data.get("triggers", [])
            }
            
            # Parse nodes
            nodes = {}
            for node_id, node_data in data.get("nodes", {}).items():
                node = self._parse_node(node_id, node_data)
                nodes[node_id] = node
            
            self.adventures[adventure_id] = nodes
            
        except Exception as e:
            print(f"Error loading adventure {filepath}: {e}")
    
    def _parse_node(self, node_id: str, data: Dict[str, Any]) -> AdventureNode:
        """Parse a node from YAML data"""
        choices = []
        for choice_data in data.get("choices", []):
            choice = Choice(
                label=choice_data.get("label", "Continue"),
                next=choice_data.get("next"),
                action=choice_data.get("action"),
                inputs=choice_data.get("inputs"),
                condition=choice_data.get("condition")
            )
            choices.append(choice)
        
        return AdventureNode(
            id=node_id,
            prompt=data.get("prompt", ""),
            choices=choices,
            action=data.get("action"),
            inputs=data.get("inputs"),
            next=data.get("next"),
            is_end=data.get("end", False) or node_id == "end"
        )
    
    def list_adventures(self) -> List[Dict[str, str]]:
        """List all available adventures"""
        return [
            {
                "id": aid,
                "name": meta["name"],
                "description": meta["description"]
            }
            for aid, meta in self.adventure_metadata.items()
        ]
    
    def start_adventure(self, adventure_id: str, variables: Dict[str, Any] = None) -> AdventureResponse:
        """Start a new adventure"""
        if adventure_id not in self.adventures:
            return AdventureResponse(
                text=f"Adventure '{adventure_id}' not found. Available: {', '.join(self.adventures.keys())}"
            )
        
        meta = self.adventure_metadata[adventure_id]
        start_node = meta["start"]
        
        self.current_state = AdventureState(
            adventure_id=adventure_id,
            current_node=start_node,
            variables=variables or {},
            history=[start_node]
        )
        
        return self._process_current_node()
    
    def process_choice(self, choice_input: str) -> AdventureResponse:
        """Process user's choice in the current adventure"""
        if not self.current_state:
            return AdventureResponse(text="No adventure is currently active.")
        
        nodes = self.adventures[self.current_state.adventure_id]
        current_node = nodes.get(self.current_state.current_node)
        
        if not current_node:
            self.current_state = None
            return AdventureResponse(text="Adventure error: node not found.", is_end=True)
        
        # Find matching choice
        choice_lower = choice_input.lower().strip()
        selected_choice = None
        
        # Try to match by number
        if choice_lower.isdigit():
            idx = int(choice_lower) - 1
            if 0 <= idx < len(current_node.choices):
                selected_choice = current_node.choices[idx]
        
        # Try to match by label
        if not selected_choice:
            for choice in current_node.choices:
                if choice_lower in choice.label.lower():
                    selected_choice = choice
                    break
        
        # Try to match by first letter
        if not selected_choice:
            for i, choice in enumerate(current_node.choices):
                if choice_lower == chr(ord('a') + i):
                    selected_choice = choice
                    break
        
        if not selected_choice:
            return AdventureResponse(
                text=f"Invalid choice. Please select from the options above.",
                choices=self._format_choices(current_node.choices)
            )
        
        # Execute choice action if present
        action_result = None
        if selected_choice.action:
            action_result = {
                "workflow": selected_choice.action,
                "inputs": self._interpolate_inputs(selected_choice.inputs or {})
            }
            self.current_state.actions_triggered.append(action_result)
        
        # Move to next node
        next_node_id = selected_choice.next
        
        if not next_node_id or next_node_id == "end":
            self.current_state = None
            return AdventureResponse(
                text="Adventure complete!",
                action=action_result["workflow"] if action_result else None,
                inputs=action_result["inputs"] if action_result else None,
                is_end=True
            )
        
        self.current_state.current_node = next_node_id
        self.current_state.history.append(next_node_id)
        
        response = self._process_current_node()
        
        # Include action from choice
        if action_result:
            response.action = action_result["workflow"]
            response.inputs = action_result["inputs"]
        
        return response
    
    def _process_current_node(self) -> AdventureResponse:
        """Process the current node and return response"""
        nodes = self.adventures[self.current_state.adventure_id]
        node = nodes.get(self.current_state.current_node)
        
        if not node:
            self.current_state = None
            return AdventureResponse(text="Adventure error.", is_end=True)
        
        # Check if this is an end node
        if node.is_end:
            adventure_id = self.current_state.adventure_id
            self.current_state = None
            return AdventureResponse(
                text=node.prompt or "Adventure complete!",
                is_end=True,
                adventure_id=adventure_id
            )
        
        # Execute node action if present
        action = None
        inputs = None
        if node.action:
            action = node.action
            inputs = self._interpolate_inputs(node.inputs or {})
            self.current_state.actions_triggered.append({
                "workflow": action,
                "inputs": inputs
            })
        
        # If no choices but has next, auto-advance
        if not node.choices and node.next:
            self.current_state.current_node = node.next
            self.current_state.history.append(node.next)
            
            next_response = self._process_current_node()
            
            # Prepend current node's prompt
            if node.prompt:
                next_response.text = f"{node.prompt}\n\n{next_response.text}"
            
            return next_response
        
        return AdventureResponse(
            text=self._interpolate_text(node.prompt),
            choices=self._format_choices(node.choices) if node.choices else None,
            action=action,
            inputs=inputs,
            adventure_id=self.current_state.adventure_id
        )
    
    def _format_choices(self, choices: List[Choice]) -> List[Dict[str, str]]:
        """Format choices for display"""
        return [
            {"value": str(i + 1), "label": choice.label}
            for i, choice in enumerate(choices)
            if self._check_condition(choice.condition)
        ]
    
    def _check_condition(self, condition: Optional[str]) -> bool:
        """Check if a condition is met"""
        if not condition:
            return True
        
        try:
            return eval(condition, {"__builtins__": {}}, self.current_state.variables)
        except:
            return True
    
    def _interpolate_text(self, text: str) -> str:
        """Interpolate variables in text"""
        if not self.current_state:
            return text
        
        for key, value in self.current_state.variables.items():
            text = text.replace(f"{{{key}}}", str(value))
            text = text.replace(f"${{{key}}}", str(value))
        
        return text
    
    def _interpolate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Interpolate variables in action inputs"""
        if not self.current_state:
            return inputs
        
        result = {}
        for key, value in inputs.items():
            if isinstance(value, str):
                for var_key, var_value in self.current_state.variables.items():
                    value = value.replace(f"{{{var_key}}}", str(var_value))
                    value = value.replace(f"${{{var_key}}}", str(var_value))
            result[key] = value
        
        return result
    
    def set_variable(self, name: str, value: Any):
        """Set a variable in the current adventure"""
        if self.current_state:
            self.current_state.variables[name] = value
    
    def cancel_adventure(self) -> AdventureResponse:
        """Cancel the current adventure"""
        if self.current_state:
            adventure_id = self.current_state.adventure_id
            self.current_state = None
            return AdventureResponse(
                text=f"Adventure '{adventure_id}' cancelled.",
                is_end=True
            )
        return AdventureResponse(text="No adventure to cancel.")
    
    def get_state(self) -> Optional[Dict[str, Any]]:
        """Get the current adventure state"""
        if not self.current_state:
            return None
        
        return {
            "adventure_id": self.current_state.adventure_id,
            "current_node": self.current_state.current_node,
            "variables": self.current_state.variables,
            "history": self.current_state.history,
            "actions_triggered": self.current_state.actions_triggered
        }
    
    def check_triggers(self, input_text: str) -> Optional[str]:
        """Check if input triggers an adventure"""
        input_lower = input_text.lower()
        
        for adventure_id, meta in self.adventure_metadata.items():
            for trigger in meta.get("triggers", []):
                if trigger.lower() in input_lower:
                    return adventure_id
        
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SAMPLE ADVENTURES
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_ADVENTURES = {
    "new-project": """
adventure: new-project
name: New Project Setup
description: Set up a new project with repository, CI/CD, and infrastructure
triggers:
  - new project
  - start project
  - create project

start: choose-type

nodes:
  choose-type:
    prompt: |
      🚀 Let's set up your new project!
      
      What type of project is this?
    choices:
      - label: "Web Application"
        next: web-stack
      - label: "API Service"
        next: api-stack
      - label: "Infrastructure Only"
        next: infra-provider
      - label: "Cancel"
        next: cancelled

  web-stack:
    prompt: |
      🌐 Web Application selected.
      
      Choose your stack:
    choices:
      - label: "React + Node.js"
        next: get-name
        inputs:
          stack: react-node
      - label: "Vue + Python"
        next: get-name
        inputs:
          stack: vue-python
      - label: "Static Site (HTML/CSS)"
        next: get-name
        inputs:
          stack: static

  api-stack:
    prompt: |
      ⚡ API Service selected.
      
      Choose your framework:
    choices:
      - label: "FastAPI (Python)"
        next: get-name
        inputs:
          stack: fastapi
      - label: "Express (Node.js)"
        next: get-name
        inputs:
          stack: express
      - label: "Go Fiber"
        next: get-name
        inputs:
          stack: go-fiber

  infra-provider:
    prompt: |
      ☁️ Infrastructure setup.
      
      Choose your cloud provider:
    choices:
      - label: "Azure"
        next: get-name
        inputs:
          provider: azure
      - label: "AWS"
        next: get-name
        inputs:
          provider: aws
      - label: "Multi-cloud"
        next: get-name
        inputs:
          provider: multi

  get-name:
    prompt: |
      📝 Great choices!
      
      What should we name this project?
      (Type the project name)
    choices:
      - label: "my-awesome-project"
        next: confirm-setup

  confirm-setup:
    prompt: |
      ✅ Ready to create your project!
      
      I will:
      - Create GitHub repository
      - Set up CI/CD pipeline
      - Configure development environment
      
      Proceed?
    choices:
      - label: "Yes, create it!"
        action: create-project
        next: creating
      - label: "No, go back"
        next: choose-type

  creating:
    prompt: |
      ⏳ Creating your project...
      
      [Workflow triggered: create-project]
    action: create-project
    next: complete

  complete:
    prompt: |
      🎉 Project created successfully!
      
      Your repository is ready at:
      https://github.com/orgitcog/{project_name}
      
      Next steps:
      - Clone the repository
      - Run `npm install` or `pip install -r requirements.txt`
      - Start developing!
    end: true

  cancelled:
    prompt: "Project setup cancelled. Come back anytime!"
    end: true
""",

    "incident-response": """
adventure: incident-response
name: Incident Response
description: Guided incident response workflow
triggers:
  - production down
  - incident
  - outage
  - emergency

start: assess-severity

nodes:
  assess-severity:
    prompt: |
      🚨 INCIDENT RESPONSE ACTIVATED
      
      Running initial diagnostics...
      
      What's the severity level?
    choices:
      - label: "🔴 Critical - Complete outage"
        next: critical-response
        inputs:
          severity: critical
      - label: "🟠 High - Major functionality impacted"
        next: high-response
        inputs:
          severity: high
      - label: "🟡 Medium - Some users affected"
        next: medium-response
        inputs:
          severity: medium
      - label: "False alarm - Cancel"
        next: cancelled

  critical-response:
    prompt: |
      🔴 CRITICAL INCIDENT
      
      Immediate actions:
      1. Notifying on-call team
      2. Creating incident channel
      3. Checking recent deployments
      
      What symptoms are you seeing?
    action: notify-oncall
    choices:
      - label: "500 errors / Server errors"
        next: check-deployments
      - label: "Timeouts / Slow responses"
        next: check-resources
      - label: "Authentication failures"
        next: check-auth
      - label: "Database errors"
        next: check-database

  high-response:
    prompt: |
      🟠 HIGH SEVERITY INCIDENT
      
      What's the primary symptom?
    choices:
      - label: "Performance degradation"
        next: check-resources
      - label: "Feature not working"
        next: check-deployments
      - label: "Intermittent errors"
        next: check-logs

  medium-response:
    prompt: |
      🟡 MEDIUM SEVERITY INCIDENT
      
      Let's investigate. What's happening?
    choices:
      - label: "Some requests failing"
        next: check-logs
      - label: "Slow for some users"
        next: check-resources
      - label: "UI issues"
        next: check-deployments

  check-deployments:
    prompt: |
      📦 Checking recent deployments...
      
      Found: Deploy #142 (2 hours ago)
      
      Options:
    action: get-recent-deployments
    choices:
      - label: "Rollback to previous version"
        next: confirm-rollback
      - label: "View deployment diff"
        next: view-diff
      - label: "Continue investigation"
        next: check-logs

  check-resources:
    prompt: |
      📊 Checking system resources...
      
      [Running health checks]
    action: health-check
    choices:
      - label: "Scale up resources"
        next: scale-up
      - label: "Check specific service"
        next: check-logs
      - label: "View metrics dashboard"
        action: open-dashboard
        next: check-resources

  check-auth:
    prompt: |
      🔐 Checking authentication systems...
      
      [Verifying identity providers]
    action: check-auth-status
    choices:
      - label: "Restart auth service"
        next: confirm-restart
      - label: "Check Azure AD status"
        action: check-azure-ad
        next: check-auth
      - label: "View auth logs"
        next: check-logs

  check-database:
    prompt: |
      🗄️ Checking database status...
      
      [Running database diagnostics]
    action: check-db-status
    choices:
      - label: "Failover to replica"
        next: confirm-failover
      - label: "Clear connection pool"
        action: clear-db-pool
        next: check-database
      - label: "View slow queries"
        next: check-logs

  check-logs:
    prompt: |
      📋 Analyzing logs...
      
      [Searching for errors in last hour]
    action: analyze-logs
    choices:
      - label: "View full error details"
        action: get-error-details
        next: resolution-options
      - label: "Search for specific pattern"
        next: search-logs
      - label: "Go to resolution options"
        next: resolution-options

  confirm-rollback:
    prompt: |
      ⚠️ CONFIRM ROLLBACK
      
      This will rollback production to the previous deployment.
      All users will be affected during the rollback (est. 3 min).
      
      Proceed with rollback?
    choices:
      - label: "Yes, rollback now"
        action: rollback-production
        next: rollback-in-progress
      - label: "No, try something else"
        next: resolution-options

  rollback-in-progress:
    prompt: |
      🔄 Rollback in progress...
      
      [Workflow: rollback-production triggered]
      
      ETA: 3 minutes
      
      I'll notify the team and update the status page.
    action: update-status-page
    next: post-incident

  resolution-options:
    prompt: |
      🔧 Resolution Options
      
      What would you like to try?
    choices:
      - label: "Rollback deployment"
        next: confirm-rollback
      - label: "Scale up resources"
        next: scale-up
      - label: "Restart services"
        next: confirm-restart
      - label: "Escalate to engineering"
        next: escalate

  scale-up:
    prompt: |
      📈 Scaling up resources...
      
      [Increasing capacity]
    action: scale-up-resources
    next: post-incident

  confirm-restart:
    prompt: |
      🔄 Confirm service restart?
      
      This will cause brief interruption.
    choices:
      - label: "Yes, restart"
        action: restart-services
        next: post-incident
      - label: "No, go back"
        next: resolution-options

  escalate:
    prompt: |
      📞 Escalating to engineering team...
      
      [Creating escalation ticket]
      [Paging senior engineers]
    action: escalate-incident
    next: post-incident

  post-incident:
    prompt: |
      ✅ Incident response actions completed.
      
      Next steps:
      - Monitor systems for 30 minutes
      - Schedule post-mortem
      - Update incident timeline
      
      Would you like to:
    choices:
      - label: "Create post-mortem document"
        action: create-postmortem
        next: complete
      - label: "Continue monitoring"
        action: start-monitoring
        next: complete
      - label: "Close incident"
        next: complete

  complete:
    prompt: |
      📋 Incident response complete.
      
      Summary of actions taken:
      - Diagnostics run
      - Resolution applied
      - Team notified
      
      Remember to complete the post-mortem within 48 hours.
    end: true

  cancelled:
    prompt: "Incident response cancelled. Stay vigilant!"
    end: true
"""
}


def create_sample_adventures(output_dir: str):
    """Create sample adventure YAML files"""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    for name, content in SAMPLE_ADVENTURES.items():
        filepath = path / f"{name}.yaml"
        with open(filepath, 'w') as f:
            f.write(content.strip())
        print(f"Created: {filepath}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI for testing adventures"""
    import sys
    
    # Create sample adventures if needed
    adventures_dir = os.path.join(os.path.dirname(__file__), "..", "adventures")
    if not os.path.exists(adventures_dir):
        create_sample_adventures(adventures_dir)
    
    engine = AdventureEngine(adventures_dir)
    
    print("Adventure Engine - Choose Your Own DevOps")
    print("=" * 50)
    print("\nAvailable adventures:")
    for adv in engine.list_adventures():
        print(f"  - {adv['id']}: {adv['name']}")
    print("\nType 'start <adventure>' to begin, 'quit' to exit")
    print("-" * 50)
    
    while True:
        try:
            if engine.active:
                prompt = f"[{engine.current_state.adventure_id}] Choice: "
            else:
                prompt = "> "
            
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                break
            
            if user_input.lower() == "cancel":
                response = engine.cancel_adventure()
                print(f"\n{response.text}\n")
                continue
            
            if user_input.lower().startswith("start "):
                adventure_id = user_input[6:].strip()
                response = engine.start_adventure(adventure_id)
            elif engine.active:
                response = engine.process_choice(user_input)
            else:
                # Check for triggers
                triggered = engine.check_triggers(user_input)
                if triggered:
                    response = engine.start_adventure(triggered)
                else:
                    print("No adventure active. Type 'start <adventure>' to begin.")
                    continue
            
            print(f"\n{response.text}")
            
            if response.choices:
                print("\nChoices:")
                for choice in response.choices:
                    print(f"  [{choice['value']}] {choice['label']}")
            
            if response.action:
                print(f"\n[ACTION] {response.action}")
                if response.inputs:
                    print(f"[INPUTS] {json.dumps(response.inputs)}")
            
            print()
            
            if response.is_end:
                print("-" * 50)
        
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()
