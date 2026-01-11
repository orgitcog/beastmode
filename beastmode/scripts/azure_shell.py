#!/usr/bin/env python3
"""
Azure Cloud Shell Helper

Provides utilities for working with Azure services from the command line,
simulating Azure Cloud Shell functionality in the Beast Mode environment.

Features:
- Azure AD authentication
- Resource management helpers
- Azure REST API client
- Cloud Shell-like commands

Usage:
    python3 azure_shell.py [command] [options]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Configuration
CONFIG_DIR = Path.home() / ".beastmode"
AZURE_CONFIG = CONFIG_DIR / "azure_config.json"

# Azure endpoints
AZURE_LOGIN_URL = "https://login.microsoftonline.com"
AZURE_MANAGEMENT_URL = "https://management.azure.com"
AZURE_GRAPH_URL = "https://graph.microsoft.com"

# ANSI colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def print_banner():
    """Print the Azure Shell banner"""
    banner = f"""
{Colors.BLUE}╔══════════════════════════════════════════════════════════════════╗
║  {Colors.BOLD}Azure Cloud Shell Helper{Colors.BLUE}                                       ║
║  {Colors.DIM}Beast Mode Azure Integration{Colors.BLUE}                                   ║
╚══════════════════════════════════════════════════════════════════╝{Colors.ENDC}
"""
    print(banner)

class AzureClient:
    """Azure REST API Client"""
    
    def __init__(self):
        self.tenant_id = os.environ.get("AZURE_TENANT_ID")
        self.client_id = os.environ.get("AZURE_CLIENT_ID")
        self.client_secret = os.environ.get("AZURE_CLIENT_SECRET")
        self.subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
        
        self._management_token = None
        self._graph_token = None
    
    def _get_token(self, resource: str) -> str:
        """Get an access token for the specified resource."""
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Missing Azure credentials. Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
        
        token_url = f"{AZURE_LOGIN_URL}/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": f"{resource}/.default",
            "grant_type": "client_credentials"
        }
        
        response = requests.post(token_url, data=data, timeout=30)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
    
    def get_management_token(self) -> str:
        """Get Azure Management API token."""
        if not self._management_token:
            self._management_token = self._get_token(AZURE_MANAGEMENT_URL)
        return self._management_token
    
    def get_graph_token(self) -> str:
        """Get Microsoft Graph API token."""
        if not self._graph_token:
            self._graph_token = self._get_token(AZURE_GRAPH_URL)
        return self._graph_token
    
    def management_request(self, method: str, endpoint: str, data: dict = None, api_version: str = "2021-04-01") -> dict:
        """Make a request to Azure Management API."""
        token = self.get_management_token()
        
        url = f"{AZURE_MANAGEMENT_URL}{endpoint}"
        if "?" in url:
            url += f"&api-version={api_version}"
        else:
            url += f"?api-version={api_version}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == 204:
            return {}
        
        return response.json() if response.text else {}
    
    def graph_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make a request to Microsoft Graph API."""
        token = self.get_graph_token()
        
        url = f"{AZURE_GRAPH_URL}/v1.0{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == 204:
            return {}
        
        return response.json() if response.text else {}
    
    # Subscription operations
    def list_subscriptions(self) -> list:
        """List Azure subscriptions."""
        result = self.management_request("GET", "/subscriptions")
        return result.get("value", [])
    
    # Resource Group operations
    def list_resource_groups(self) -> list:
        """List resource groups in the current subscription."""
        if not self.subscription_id:
            raise ValueError("AZURE_SUBSCRIPTION_ID not set")
        
        result = self.management_request(
            "GET", 
            f"/subscriptions/{self.subscription_id}/resourcegroups"
        )
        return result.get("value", [])
    
    def create_resource_group(self, name: str, location: str) -> dict:
        """Create a resource group."""
        if not self.subscription_id:
            raise ValueError("AZURE_SUBSCRIPTION_ID not set")
        
        data = {"location": location}
        return self.management_request(
            "PUT",
            f"/subscriptions/{self.subscription_id}/resourcegroups/{name}",
            data=data
        )
    
    # Resource operations
    def list_resources(self, resource_group: str = None) -> list:
        """List resources."""
        if not self.subscription_id:
            raise ValueError("AZURE_SUBSCRIPTION_ID not set")
        
        if resource_group:
            endpoint = f"/subscriptions/{self.subscription_id}/resourceGroups/{resource_group}/resources"
        else:
            endpoint = f"/subscriptions/{self.subscription_id}/resources"
        
        result = self.management_request("GET", endpoint)
        return result.get("value", [])
    
    # Azure AD operations (via Graph)
    def get_tenant_info(self) -> dict:
        """Get tenant information."""
        result = self.graph_request("GET", "/organization")
        orgs = result.get("value", [])
        return orgs[0] if orgs else {}
    
    def list_users(self, top: int = 100) -> list:
        """List Azure AD users."""
        result = self.graph_request("GET", f"/users?$top={top}")
        return result.get("value", [])
    
    def list_groups(self, top: int = 100) -> list:
        """List Azure AD groups."""
        result = self.graph_request("GET", f"/groups?$top={top}")
        return result.get("value", [])


def cmd_login(args):
    """Test Azure login"""
    print(f"\n{Colors.BOLD}Testing Azure Authentication...{Colors.ENDC}")
    
    try:
        client = AzureClient()
        
        # Test Graph API
        print(f"\n{Colors.CYAN}Microsoft Graph API:{Colors.ENDC}")
        tenant = client.get_tenant_info()
        if tenant:
            print(f"  {Colors.GREEN}✓{Colors.ENDC} Connected to: {tenant.get('displayName', 'Unknown')}")
            print(f"    Tenant ID: {tenant.get('id', 'Unknown')}")
        
        # Test Management API (if subscription is set)
        if client.subscription_id:
            print(f"\n{Colors.CYAN}Azure Management API:{Colors.ENDC}")
            subs = client.list_subscriptions()
            for sub in subs:
                if sub.get("subscriptionId") == client.subscription_id:
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} Subscription: {sub.get('displayName', 'Unknown')}")
                    print(f"    State: {sub.get('state', 'Unknown')}")
                    break
        else:
            print(f"\n{Colors.YELLOW}Note: AZURE_SUBSCRIPTION_ID not set. Management API features limited.{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.RED}✗ Authentication failed: {e}{Colors.ENDC}")

def cmd_account(args):
    """Show account information"""
    print(f"\n{Colors.BOLD}Azure Account Information{Colors.ENDC}")
    print("=" * 50)
    
    try:
        client = AzureClient()
        
        # Tenant info
        tenant = client.get_tenant_info()
        print(f"\n{Colors.CYAN}Tenant:{Colors.ENDC}")
        print(f"  Display Name: {tenant.get('displayName', 'N/A')}")
        print(f"  Tenant ID: {tenant.get('id', 'N/A')}")
        print(f"  Domains: {', '.join([d.get('id', '') for d in tenant.get('verifiedDomains', [])])}")
        
        # Subscription info
        if client.subscription_id:
            subs = client.list_subscriptions()
            for sub in subs:
                if sub.get("subscriptionId") == client.subscription_id:
                    print(f"\n{Colors.CYAN}Subscription:{Colors.ENDC}")
                    print(f"  Display Name: {sub.get('displayName', 'N/A')}")
                    print(f"  Subscription ID: {sub.get('subscriptionId', 'N/A')}")
                    print(f"  State: {sub.get('state', 'N/A')}")
                    break
        
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def cmd_group(args):
    """Resource group operations"""
    try:
        client = AzureClient()
        
        if args.list:
            print(f"\n{Colors.BOLD}Resource Groups:{Colors.ENDC}")
            groups = client.list_resource_groups()
            for group in groups:
                print(f"  • {group.get('name', 'N/A')} ({group.get('location', 'N/A')})")
        
        elif args.create:
            name = args.create
            location = args.location or "eastus"
            print(f"\n{Colors.CYAN}Creating resource group: {name} in {location}...{Colors.ENDC}")
            result = client.create_resource_group(name, location)
            print(f"{Colors.GREEN}✓ Created: {result.get('name', name)}{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def cmd_resource(args):
    """Resource operations"""
    try:
        client = AzureClient()
        
        print(f"\n{Colors.BOLD}Resources:{Colors.ENDC}")
        resources = client.list_resources(args.resource_group)
        
        for resource in resources[:20]:  # Limit to 20
            rtype = resource.get("type", "").split("/")[-1]
            print(f"  • {resource.get('name', 'N/A')} ({rtype})")
        
        if len(resources) > 20:
            print(f"  ... and {len(resources) - 20} more")
        
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def cmd_ad(args):
    """Azure AD operations"""
    try:
        client = AzureClient()
        
        if args.users:
            print(f"\n{Colors.BOLD}Azure AD Users:{Colors.ENDC}")
            users = client.list_users(top=args.top or 10)
            for user in users:
                print(f"  • {user.get('displayName', 'N/A')} ({user.get('userPrincipalName', 'N/A')})")
        
        elif args.groups:
            print(f"\n{Colors.BOLD}Azure AD Groups:{Colors.ENDC}")
            groups = client.list_groups(top=args.top or 10)
            for group in groups:
                print(f"  • {group.get('displayName', 'N/A')}")
        
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def cmd_rest(args):
    """Make a REST API call"""
    try:
        client = AzureClient()
        
        method = args.method.upper()
        uri = args.uri
        
        # Determine which API to use
        if uri.startswith("/subscriptions") or uri.startswith("/providers"):
            print(f"\n{Colors.CYAN}{method} (Management API) {uri}{Colors.ENDC}")
            result = client.management_request(method, uri)
        else:
            print(f"\n{Colors.CYAN}{method} (Graph API) {uri}{Colors.ENDC}")
            result = client.graph_request(method, uri)
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")

def cmd_interactive(args):
    """Start interactive mode"""
    print_banner()
    print(f"{Colors.DIM}Type 'help' for commands, 'exit' to quit{Colors.ENDC}\n")
    
    client = None
    try:
        client = AzureClient()
        tenant = client.get_tenant_info()
        print(f"{Colors.GREEN}Connected to: {tenant.get('displayName', 'Unknown')}{Colors.ENDC}\n")
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: {e}{Colors.ENDC}\n")
    
    while True:
        try:
            cmd = input(f"{Colors.BLUE}az>{Colors.ENDC} ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split()
            command = parts[0].lower()
            
            if command in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            elif command == "help":
                print(f"""
{Colors.BOLD}Commands:{Colors.ENDC}
  login              - Test authentication
  account            - Show account info
  ad users           - List Azure AD users
  ad groups          - List Azure AD groups
  group list         - List resource groups
  resource list      - List resources
  rest GET <uri>     - Make REST API call
  clear              - Clear screen
  exit               - Exit
""")
            elif command == "login":
                cmd_login(None)
            elif command == "account":
                cmd_account(None)
            elif command == "ad" and len(parts) > 1:
                if parts[1] == "users":
                    cmd_ad(argparse.Namespace(users=True, groups=False, top=10))
                elif parts[1] == "groups":
                    cmd_ad(argparse.Namespace(users=False, groups=True, top=10))
            elif command == "group" and len(parts) > 1 and parts[1] == "list":
                cmd_group(argparse.Namespace(list=True, create=None, location=None))
            elif command == "resource" and len(parts) > 1 and parts[1] == "list":
                cmd_resource(argparse.Namespace(resource_group=None))
            elif command == "rest" and len(parts) >= 3:
                cmd_rest(argparse.Namespace(method=parts[1], uri=parts[2]))
            elif command == "clear":
                os.system('clear')
            else:
                print(f"{Colors.YELLOW}Unknown command. Type 'help' for available commands.{Colors.ENDC}")
                
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit")
        except EOFError:
            break

def cmd_help(args):
    """Show help"""
    print_banner()
    print(f"""
{Colors.BOLD}Usage:{Colors.ENDC}
  azure_shell.py <command> [options]

{Colors.BOLD}Commands:{Colors.ENDC}
  {Colors.CYAN}login{Colors.ENDC}        Test Azure authentication
  {Colors.CYAN}account{Colors.ENDC}      Show account information
  {Colors.CYAN}group{Colors.ENDC}        Resource group operations (--list, --create)
  {Colors.CYAN}resource{Colors.ENDC}     List resources
  {Colors.CYAN}ad{Colors.ENDC}           Azure AD operations (--users, --groups)
  {Colors.CYAN}rest{Colors.ENDC}         Make REST API call
  {Colors.CYAN}interactive{Colors.ENDC}  Start interactive mode

{Colors.BOLD}Examples:{Colors.ENDC}
  azure_shell.py login
  azure_shell.py account
  azure_shell.py ad --users --top 20
  azure_shell.py group --list
  azure_shell.py rest --method GET --uri /users
  azure_shell.py interactive

{Colors.BOLD}Environment Variables:{Colors.ENDC}
  AZURE_TENANT_ID         Azure AD Tenant ID
  AZURE_CLIENT_ID         Azure AD Application Client ID
  AZURE_CLIENT_SECRET     Azure AD Application Client Secret
  AZURE_SUBSCRIPTION_ID   Azure Subscription ID (for management API)
""")

def main():
    parser = argparse.ArgumentParser(
        description='Azure Cloud Shell Helper',
        add_help=False
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Login command
    login_parser = subparsers.add_parser('login', help='Test authentication')
    login_parser.set_defaults(func=cmd_login)
    
    # Account command
    account_parser = subparsers.add_parser('account', help='Show account info')
    account_parser.set_defaults(func=cmd_account)
    
    # Group command
    group_parser = subparsers.add_parser('group', help='Resource group operations')
    group_parser.add_argument('--list', action='store_true', help='List resource groups')
    group_parser.add_argument('--create', help='Create a resource group')
    group_parser.add_argument('--location', help='Location for new resource group')
    group_parser.set_defaults(func=cmd_group)
    
    # Resource command
    resource_parser = subparsers.add_parser('resource', help='List resources')
    resource_parser.add_argument('--resource-group', help='Filter by resource group')
    resource_parser.set_defaults(func=cmd_resource)
    
    # AD command
    ad_parser = subparsers.add_parser('ad', help='Azure AD operations')
    ad_parser.add_argument('--users', action='store_true', help='List users')
    ad_parser.add_argument('--groups', action='store_true', help='List groups')
    ad_parser.add_argument('--top', type=int, help='Number of results')
    ad_parser.set_defaults(func=cmd_ad)
    
    # REST command
    rest_parser = subparsers.add_parser('rest', help='Make REST API call')
    rest_parser.add_argument('--method', default='GET', help='HTTP method')
    rest_parser.add_argument('--uri', required=True, help='API URI')
    rest_parser.set_defaults(func=cmd_rest)
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive mode')
    interactive_parser.set_defaults(func=cmd_interactive)
    
    # Help command
    help_parser = subparsers.add_parser('help', help='Show help')
    help_parser.set_defaults(func=cmd_help)
    
    args = parser.parse_args()
    
    if args.command is None:
        cmd_help(args)
    else:
        args.func(args)

if __name__ == '__main__':
    main()
