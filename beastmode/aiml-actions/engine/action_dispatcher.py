#!/usr/bin/env python3
"""
Action Dispatcher - GitHub Actions Workflow Generator and Dispatcher

Generates GitHub Actions workflows from AIML patterns and dispatches
workflow runs via the GitHub API.
"""

import os
import json
import yaml
import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WorkflowDefinition:
    """Definition of a GitHub Actions workflow"""
    name: str
    description: str
    inputs: Dict[str, Dict[str, Any]]
    steps: List[Dict[str, Any]]
    runs_on: str = "ubuntu-latest"


@dataclass
class DispatchResult:
    """Result of a workflow dispatch"""
    success: bool
    workflow_id: Optional[str] = None
    run_id: Optional[int] = None
    run_url: Optional[str] = None
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

WORKFLOW_TEMPLATES = {
    # Azure AD Operations
    "azure-create-tenant": WorkflowDefinition(
        name="Create Azure AD Tenant",
        description="Create a new Azure AD tenant (requires Azure subscription)",
        inputs={
            "name": {"description": "Tenant name", "required": True, "type": "string"},
            "domain": {"description": "Initial domain prefix", "required": False, "type": "string"}
        },
        steps=[
            {"name": "Checkout", "uses": "actions/checkout@v4"},
            {"name": "Setup Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
            {"name": "Install dependencies", "run": "pip install azure-identity azure-mgmt-subscription"},
            {"name": "Create Tenant", "run": "python god-mode/scripts/rapid_provision.py --action create-tenant --name ${{ inputs.name }}",
             "env": {"AZURE_TENANT_ID": "${{ secrets.AZURE_TENANT_ID }}", "AZURE_CLIENT_ID": "${{ secrets.AZURE_CLIENT_ID }}", "AZURE_CLIENT_SECRET": "${{ secrets.AZURE_CLIENT_SECRET }}"}}
        ]
    ),
    
    "azure-create-users": WorkflowDefinition(
        name="Create Azure AD Users",
        description="Bulk create users in Azure AD",
        inputs={
            "count": {"description": "Number of users to create", "required": True, "type": "number"},
            "domain": {"description": "User domain", "required": False, "type": "string"},
            "prefix": {"description": "Username prefix", "required": False, "type": "string", "default": "user"}
        },
        steps=[
            {"name": "Checkout", "uses": "actions/checkout@v4"},
            {"name": "Setup Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
            {"name": "Install dependencies", "run": "pip install msal requests"},
            {"name": "Create Users", "run": "python god-mode/scripts/rapid_provision.py --action create-users --count ${{ inputs.count }} --prefix ${{ inputs.prefix }}",
             "env": {"AZURE_TENANT_ID": "${{ secrets.AZURE_TENANT_ID }}", "AZURE_CLIENT_ID": "${{ secrets.AZURE_CLIENT_ID }}", "AZURE_CLIENT_SECRET": "${{ secrets.AZURE_CLIENT_SECRET }}"}}
        ]
    ),
    
    "azure-create-groups": WorkflowDefinition(
        name="Create Azure AD Groups",
        description="Bulk create groups in Azure AD",
        inputs={
            "count": {"description": "Number of groups to create", "required": True, "type": "number"},
            "prefix": {"description": "Group name prefix", "required": False, "type": "string", "default": "group"}
        },
        steps=[
            {"name": "Checkout", "uses": "actions/checkout@v4"},
            {"name": "Setup Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
            {"name": "Install dependencies", "run": "pip install msal requests"},
            {"name": "Create Groups", "run": "python god-mode/scripts/rapid_provision.py --action create-groups --count ${{ inputs.count }} --prefix ${{ inputs.prefix }}",
             "env": {"AZURE_TENANT_ID": "${{ secrets.AZURE_TENANT_ID }}", "AZURE_CLIENT_ID": "${{ secrets.AZURE_CLIENT_ID }}", "AZURE_CLIENT_SECRET": "${{ secrets.AZURE_CLIENT_SECRET }}"}}
        ]
    ),
    
    # GitHub Operations
    "github-create-repo": WorkflowDefinition(
        name="Create GitHub Repository",
        description="Create a new GitHub repository",
        inputs={
            "name": {"description": "Repository name", "required": True, "type": "string"},
            "org": {"description": "Organization (optional)", "required": False, "type": "string"},
            "private": {"description": "Private repository", "required": False, "type": "boolean", "default": False},
            "template": {"description": "Template repository", "required": False, "type": "string"}
        },
        steps=[
            {"name": "Create Repository", "run": """
if [ -n "${{ inputs.org }}" ]; then
  gh repo create ${{ inputs.org }}/${{ inputs.name }} --public --clone
else
  gh repo create ${{ inputs.name }} --public --clone
fi
""", "env": {"GH_TOKEN": "${{ secrets.BEAST_PAT }}"}}
        ]
    ),
    
    "github-bulk-repos": WorkflowDefinition(
        name="Bulk Create GitHub Repositories",
        description="Create multiple repositories at once",
        inputs={
            "count": {"description": "Number of repositories", "required": True, "type": "number"},
            "org": {"description": "Organization", "required": True, "type": "string"},
            "prefix": {"description": "Repository name prefix", "required": False, "type": "string", "default": "repo"}
        },
        steps=[
            {"name": "Checkout", "uses": "actions/checkout@v4"},
            {"name": "Bulk Create", "run": """
for i in $(seq 1 ${{ inputs.count }}); do
  gh repo create ${{ inputs.org }}/${{ inputs.prefix }}-$i --public
  echo "Created ${{ inputs.org }}/${{ inputs.prefix }}-$i"
done
""", "env": {"GH_TOKEN": "${{ secrets.BEAST_PAT }}"}}
        ]
    ),
    
    # Sync Operations
    "sync-azure-github": WorkflowDefinition(
        name="Sync Azure AD to GitHub",
        description="Synchronize Azure AD groups/users to GitHub teams",
        inputs={
            "resource": {"description": "Resource to sync (users, groups, all)", "required": True, "type": "string"},
            "org": {"description": "GitHub organization", "required": True, "type": "string"}
        },
        steps=[
            {"name": "Checkout", "uses": "actions/checkout@v4"},
            {"name": "Setup Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
            {"name": "Install dependencies", "run": "pip install msal requests PyGithub"},
            {"name": "Sync", "run": "python god-mode/scripts/org_sync_toolkit.py --action sync --resource ${{ inputs.resource }} --org ${{ inputs.org }}",
             "env": {
                 "AZURE_TENANT_ID": "${{ secrets.AZURE_TENANT_ID }}",
                 "AZURE_CLIENT_ID": "${{ secrets.AZURE_CLIENT_ID }}",
                 "AZURE_CLIENT_SECRET": "${{ secrets.AZURE_CLIENT_SECRET }}",
                 "GH_TOKEN": "${{ secrets.BEAST_PAT }}"
             }}
        ]
    ),
    
    # Mass Provisioning
    "mass-provision": WorkflowDefinition(
        name="Mass Infrastructure Provisioning",
        description="Provision multiple tenants, orgs, and users at once",
        inputs={
            "tenants": {"description": "Number of tenants", "required": True, "type": "number"},
            "orgs": {"description": "Orgs per tenant", "required": True, "type": "number"},
            "users": {"description": "Users per org", "required": True, "type": "number"}
        },
        steps=[
            {"name": "Checkout", "uses": "actions/checkout@v4"},
            {"name": "Setup Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
            {"name": "Install dependencies", "run": "pip install msal requests PyGithub azure-identity"},
            {"name": "Mass Provision", "run": "python god-mode/scripts/rapid_provision.py --action mass-provision --tenants ${{ inputs.tenants }} --orgs ${{ inputs.orgs }} --users ${{ inputs.users }}",
             "env": {
                 "AZURE_TENANT_ID": "${{ secrets.AZURE_TENANT_ID }}",
                 "AZURE_CLIENT_ID": "${{ secrets.AZURE_CLIENT_ID }}",
                 "AZURE_CLIENT_SECRET": "${{ secrets.AZURE_CLIENT_SECRET }}",
                 "GH_TOKEN": "${{ secrets.BEAST_PAT }}"
             }}
        ]
    ),
    
    # Incident Response
    "health-check": WorkflowDefinition(
        name="System Health Check",
        description="Run comprehensive health checks",
        inputs={
            "services": {"description": "Services to check (comma-separated)", "required": False, "type": "string", "default": "all"}
        },
        steps=[
            {"name": "Health Check", "run": """
echo "Running health checks..."
# Add your health check commands here
curl -s -o /dev/null -w "%{http_code}" https://api.github.com/status || echo "GitHub API: DOWN"
echo "Health check complete"
"""}
        ]
    ),
    
    "rollback-production": WorkflowDefinition(
        name="Rollback Production",
        description="Rollback production to previous deployment",
        inputs={
            "target": {"description": "Target deployment/commit", "required": False, "type": "string"}
        },
        steps=[
            {"name": "Rollback", "run": """
echo "Initiating rollback..."
# Add your rollback logic here
echo "Rollback complete"
"""}
        ]
    ),
    
    # Project Setup
    "create-project": WorkflowDefinition(
        name="Create New Project",
        description="Set up a new project with repo, CI/CD, and infrastructure",
        inputs={
            "name": {"description": "Project name", "required": True, "type": "string"},
            "stack": {"description": "Technology stack", "required": True, "type": "string"},
            "org": {"description": "Organization", "required": False, "type": "string"}
        },
        steps=[
            {"name": "Create Repository", "run": """
ORG="${{ inputs.org }}"
if [ -z "$ORG" ]; then ORG="orgitcog"; fi
gh repo create $ORG/${{ inputs.name }} --public --clone
cd ${{ inputs.name }}
echo "# ${{ inputs.name }}" > README.md
git add README.md
git commit -m "Initial commit"
git push origin main
""", "env": {"GH_TOKEN": "${{ secrets.BEAST_PAT }}"}},
            {"name": "Setup CI/CD", "run": """
mkdir -p .github/workflows
cat > .github/workflows/ci.yml << 'WORKFLOW'
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: echo "Building..."
WORKFLOW
git add .github/
git commit -m "Add CI/CD workflow"
git push origin main
"""}
        ]
    )
}


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════════

class ActionDispatcher:
    """
    Dispatches GitHub Actions workflows and generates workflow files.
    """
    
    def __init__(self, github_token: Optional[str] = None, repo: str = "orgitcog/beastmode"):
        self.github_token = github_token or os.environ.get("beast") or os.environ.get("GITHUB_TOKEN")
        self.repo = repo
        self.api_base = "https://api.github.com"
        self.templates = WORKFLOW_TEMPLATES
    
    def dispatch_workflow(self, workflow_name: str, inputs: Dict[str, Any] = None) -> DispatchResult:
        """Dispatch a workflow via GitHub API"""
        if not self.github_token:
            return DispatchResult(success=False, error="No GitHub token configured")
        
        # Map workflow name to file
        workflow_file = f"{workflow_name}.yml"
        
        url = f"{self.api_base}/repos/{self.repo}/actions/workflows/{workflow_file}/dispatches"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        payload = {
            "ref": "main",
            "inputs": inputs or {}
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 204:
                # Get the run ID
                run_id = self._get_latest_run_id(workflow_file)
                run_url = f"https://github.com/{self.repo}/actions/runs/{run_id}" if run_id else None
                
                return DispatchResult(
                    success=True,
                    workflow_id=workflow_name,
                    run_id=run_id,
                    run_url=run_url
                )
            else:
                return DispatchResult(
                    success=False,
                    error=f"API error: {response.status_code} - {response.text}"
                )
        except Exception as e:
            return DispatchResult(success=False, error=str(e))
    
    def _get_latest_run_id(self, workflow_file: str) -> Optional[int]:
        """Get the latest workflow run ID"""
        url = f"{self.api_base}/repos/{self.repo}/actions/workflows/{workflow_file}/runs"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            response = requests.get(url, headers=headers, params={"per_page": 1}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("workflow_runs"):
                    return data["workflow_runs"][0]["id"]
        except:
            pass
        
        return None
    
    def generate_workflow_file(self, workflow_name: str, output_dir: str = None) -> str:
        """Generate a GitHub Actions workflow YAML file"""
        if workflow_name not in self.templates:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        template = self.templates[workflow_name]
        
        # Build workflow structure
        workflow = {
            "name": template.name,
            "on": {
                "workflow_dispatch": {
                    "inputs": {}
                }
            },
            "jobs": {
                "run": {
                    "runs-on": template.runs_on,
                    "steps": template.steps
                }
            }
        }
        
        # Add inputs
        for input_name, input_config in template.inputs.items():
            workflow["on"]["workflow_dispatch"]["inputs"][input_name] = {
                "description": input_config.get("description", ""),
                "required": input_config.get("required", False),
                "type": input_config.get("type", "string")
            }
            if "default" in input_config:
                workflow["on"]["workflow_dispatch"]["inputs"][input_name]["default"] = str(input_config["default"])
        
        # Convert to YAML
        yaml_content = yaml.dump(workflow, default_flow_style=False, sort_keys=False)
        
        # Add header comment
        header = f"""# {template.name}
# {template.description}
# Generated by AIML Actions Engine
# https://github.com/orgitcog/beastmode

"""
        yaml_content = header + yaml_content
        
        # Save if output directory provided
        if output_dir:
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
            filepath = path / f"{workflow_name}.yml"
            with open(filepath, 'w') as f:
                f.write(yaml_content)
        
        return yaml_content
    
    def generate_all_workflows(self, output_dir: str):
        """Generate all workflow files"""
        for workflow_name in self.templates:
            self.generate_workflow_file(workflow_name, output_dir)
            print(f"Generated: {workflow_name}.yml")
    
    def list_workflows(self) -> List[Dict[str, str]]:
        """List all available workflow templates"""
        return [
            {
                "name": name,
                "description": template.description,
                "inputs": list(template.inputs.keys())
            }
            for name, template in self.templates.items()
        ]
    
    def add_template(self, name: str, definition: WorkflowDefinition):
        """Add a new workflow template"""
        self.templates[name] = definition
    
    def generate_from_aiml(self, pattern: str, workflow_name: str, inputs_mapping: Dict[str, int]) -> str:
        """
        Generate a workflow from an AIML pattern.
        
        Args:
            pattern: AIML pattern (e.g., "CREATE * USERS IN * ORG")
            workflow_name: Name for the generated workflow
            inputs_mapping: Map of input names to star indices
        
        Returns:
            Generated workflow YAML
        """
        # Parse pattern to extract wildcards
        parts = pattern.split()
        wildcards = [i for i, p in enumerate(parts) if p in ["*", "_", "#", "^"]]
        
        # Build inputs from mapping
        inputs = {}
        for input_name, star_index in inputs_mapping.items():
            inputs[input_name] = {
                "description": f"Value from pattern position {star_index}",
                "required": True,
                "type": "string"
            }
        
        # Create a basic workflow
        definition = WorkflowDefinition(
            name=workflow_name.replace("-", " ").title(),
            description=f"Auto-generated from pattern: {pattern}",
            inputs=inputs,
            steps=[
                {"name": "Checkout", "uses": "actions/checkout@v4"},
                {"name": "Execute", "run": f"echo 'Executing {workflow_name} with inputs: ${{{{ toJson(inputs) }}}}'"}
            ]
        )
        
        self.templates[workflow_name] = definition
        return self.generate_workflow_file(workflow_name)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI for the Action Dispatcher"""
    import sys
    
    dispatcher = ActionDispatcher()
    
    if len(sys.argv) < 2:
        print("Action Dispatcher - GitHub Actions Workflow Generator")
        print("=" * 50)
        print("\nUsage:")
        print("  python action_dispatcher.py list")
        print("  python action_dispatcher.py generate <workflow>")
        print("  python action_dispatcher.py generate-all <output_dir>")
        print("  python action_dispatcher.py dispatch <workflow> [inputs_json]")
        print("\nAvailable workflows:")
        for wf in dispatcher.list_workflows():
            print(f"  - {wf['name']}: {wf['description']}")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        print("Available Workflows:")
        print("-" * 50)
        for wf in dispatcher.list_workflows():
            print(f"\n{wf['name']}")
            print(f"  Description: {wf['description']}")
            print(f"  Inputs: {', '.join(wf['inputs']) if wf['inputs'] else 'none'}")
    
    elif command == "generate":
        if len(sys.argv) < 3:
            print("Usage: python action_dispatcher.py generate <workflow>")
            return
        
        workflow = sys.argv[2]
        try:
            yaml_content = dispatcher.generate_workflow_file(workflow)
            print(yaml_content)
        except ValueError as e:
            print(f"Error: {e}")
    
    elif command == "generate-all":
        output_dir = sys.argv[2] if len(sys.argv) > 2 else ".github/workflows"
        dispatcher.generate_all_workflows(output_dir)
        print(f"\nAll workflows generated in: {output_dir}")
    
    elif command == "dispatch":
        if len(sys.argv) < 3:
            print("Usage: python action_dispatcher.py dispatch <workflow> [inputs_json]")
            return
        
        workflow = sys.argv[2]
        inputs = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        
        result = dispatcher.dispatch_workflow(workflow, inputs)
        
        if result.success:
            print(f"✓ Workflow dispatched successfully!")
            print(f"  Workflow: {result.workflow_id}")
            if result.run_url:
                print(f"  Run URL: {result.run_url}")
        else:
            print(f"✗ Dispatch failed: {result.error}")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
