#!/usr/bin/env python3
"""
Beast Mode CLI - MS Graph & GitHub Enterprise Automation Toolkit

A comprehensive command-line interface for managing Azure AD and GitHub Enterprise
resources with full administrative capabilities.

Usage:
    python3 beastmode.py [command] [options]

Commands:
    status      - Show connection status for Azure AD and GHE
    users       - List and manage users
    groups      - List and manage groups
    teams       - List and manage GHE teams
    sync        - Synchronize organizations between Azure AD and GHE
    config      - Configure credentials and settings
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Configuration paths
CONFIG_DIR = os.path.expanduser("~/.beastmode")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, "credentials.json")

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    """Print the Beast Mode banner"""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   {Colors.BOLD}██████╗ ███████╗ █████╗ ███████╗████████╗{Colors.CYAN}                       ║
║   {Colors.BOLD}██╔══██╗██╔════╝██╔══██╗██╔════╝╚══██╔══╝{Colors.CYAN}                       ║
║   {Colors.BOLD}██████╔╝█████╗  ███████║███████╗   ██║   {Colors.CYAN}                       ║
║   {Colors.BOLD}██╔══██╗██╔══╝  ██╔══██║╚════██║   ██║   {Colors.CYAN}                       ║
║   {Colors.BOLD}██████╔╝███████╗██║  ██║███████║   ██║   {Colors.CYAN}                       ║
║   {Colors.BOLD}╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   {Colors.CYAN}                       ║
║                                                                    ║
║   {Colors.GREEN}███╗   ███╗ ██████╗ ██████╗ ███████╗{Colors.CYAN}                           ║
║   {Colors.GREEN}████╗ ████║██╔═══██╗██╔══██╗██╔════╝{Colors.CYAN}                           ║
║   {Colors.GREEN}██╔████╔██║██║   ██║██║  ██║█████╗  {Colors.CYAN}                           ║
║   {Colors.GREEN}██║╚██╔╝██║██║   ██║██║  ██║██╔══╝  {Colors.CYAN}                           ║
║   {Colors.GREEN}██║ ╚═╝ ██║╚██████╔╝██████╔╝███████╗{Colors.CYAN}                           ║
║   {Colors.GREEN}╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝{Colors.CYAN}                           ║
║                                                                    ║
║   {Colors.WARNING}MS Graph & GitHub Enterprise Automation Toolkit{Colors.CYAN}               ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════╝{Colors.ENDC}
"""
    print(banner)

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save configuration to file"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_credentials():
    """Load credentials from file or environment"""
    creds = {
        'azure_tenant_id': os.environ.get('AZURE_TENANT_ID', ''),
        'azure_client_id': os.environ.get('AZURE_CLIENT_ID', ''),
        'azure_client_secret': os.environ.get('AZURE_CLIENT_SECRET', ''),
        'ghe_instance_url': os.environ.get('GHE_INSTANCE_URL', 'https://zone.ghe.com'),
        'ghe_admin_token': os.environ.get('GHE_ADMIN_TOKEN', ''),
    }
    
    # Override with file credentials if available
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            file_creds = json.load(f)
            creds.update(file_creds)
    
    return creds

def get_azure_token(creds):
    """Get Azure AD access token"""
    if not HAS_REQUESTS:
        return None
    
    token_url = f"https://login.microsoftonline.com/{creds['azure_tenant_id']}/oauth2/v2.0/token"
    
    data = {
        'client_id': creds['azure_client_id'],
        'client_secret': creds['azure_client_secret'],
        'scope': 'https://graph.microsoft.com/.default',
        'grant_type': 'client_credentials'
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json().get('access_token')
    except Exception:
        pass
    return None

def cmd_status(args):
    """Show connection status"""
    print(f"\n{Colors.BOLD}Connection Status{Colors.ENDC}")
    print("=" * 50)
    
    creds = load_credentials()
    
    # Azure AD Status
    print(f"\n{Colors.CYAN}Azure AD / Microsoft Graph:{Colors.ENDC}")
    if creds.get('azure_tenant_id') and creds.get('azure_client_id'):
        print(f"  Tenant ID: {creds['azure_tenant_id'][:8]}...")
        print(f"  Client ID: {creds['azure_client_id'][:8]}...")
        
        if HAS_REQUESTS:
            token = get_azure_token(creds)
            if token:
                print(f"  Status: {Colors.GREEN}✓ Connected{Colors.ENDC}")
            else:
                print(f"  Status: {Colors.FAIL}✗ Authentication failed{Colors.ENDC}")
        else:
            print(f"  Status: {Colors.WARNING}⚠ requests module not available{Colors.ENDC}")
    else:
        print(f"  Status: {Colors.WARNING}⚠ Not configured{Colors.ENDC}")
    
    # GHE Status
    print(f"\n{Colors.CYAN}GitHub Enterprise:{Colors.ENDC}")
    if creds.get('ghe_instance_url') and creds.get('ghe_admin_token'):
        print(f"  Instance: {creds['ghe_instance_url']}")
        print(f"  Token: {creds['ghe_admin_token'][:8]}...")
        
        if HAS_REQUESTS:
            try:
                headers = {
                    'Authorization': f"token {creds['ghe_admin_token']}",
                    'Accept': 'application/vnd.github.v3+json'
                }
                response = requests.get(
                    f"{creds['ghe_instance_url']}/api/v3/user",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    user = response.json()
                    print(f"  User: {user.get('login')}")
                    print(f"  Status: {Colors.GREEN}✓ Connected{Colors.ENDC}")
                else:
                    print(f"  Status: {Colors.FAIL}✗ Authentication failed{Colors.ENDC}")
            except Exception as e:
                print(f"  Status: {Colors.FAIL}✗ Connection error{Colors.ENDC}")
        else:
            print(f"  Status: {Colors.WARNING}⚠ requests module not available{Colors.ENDC}")
    else:
        print(f"  Status: {Colors.WARNING}⚠ Not configured{Colors.ENDC}")
    
    print()

def cmd_users(args):
    """List users"""
    print(f"\n{Colors.BOLD}Users{Colors.ENDC}")
    print("=" * 50)
    
    creds = load_credentials()
    
    if args.source == 'azure' or args.source == 'all':
        print(f"\n{Colors.CYAN}Azure AD Users:{Colors.ENDC}")
        if HAS_REQUESTS:
            token = get_azure_token(creds)
            if token:
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/users?$top=10&$select=displayName,userPrincipalName',
                    headers=headers
                )
                if response.status_code == 200:
                    users = response.json().get('value', [])
                    for user in users:
                        print(f"  • {user.get('displayName')} ({user.get('userPrincipalName')})")
                else:
                    print(f"  {Colors.FAIL}Error fetching users{Colors.ENDC}")
            else:
                print(f"  {Colors.FAIL}Not authenticated{Colors.ENDC}")
        else:
            print(f"  {Colors.WARNING}requests module not available{Colors.ENDC}")
    
    if args.source == 'ghe' or args.source == 'all':
        print(f"\n{Colors.CYAN}GitHub Enterprise Users:{Colors.ENDC}")
        if HAS_REQUESTS and creds.get('ghe_admin_token'):
            headers = {
                'Authorization': f"token {creds['ghe_admin_token']}",
                'Accept': 'application/vnd.github.v3+json'
            }
            try:
                response = requests.get(
                    f"{creds['ghe_instance_url']}/api/v3/users?per_page=10",
                    headers=headers
                )
                if response.status_code == 200:
                    users = response.json()
                    for user in users:
                        print(f"  • {user.get('login')}")
                else:
                    print(f"  {Colors.FAIL}Error fetching users{Colors.ENDC}")
            except Exception:
                print(f"  {Colors.FAIL}Connection error{Colors.ENDC}")
        else:
            print(f"  {Colors.WARNING}Not configured or requests not available{Colors.ENDC}")
    
    print()

def cmd_groups(args):
    """List groups"""
    print(f"\n{Colors.BOLD}Groups{Colors.ENDC}")
    print("=" * 50)
    
    creds = load_credentials()
    
    print(f"\n{Colors.CYAN}Azure AD Groups:{Colors.ENDC}")
    if HAS_REQUESTS:
        token = get_azure_token(creds)
        if token:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                'https://graph.microsoft.com/v1.0/groups?$top=10&$select=displayName,description',
                headers=headers
            )
            if response.status_code == 200:
                groups = response.json().get('value', [])
                for group in groups:
                    desc = group.get('description', '')[:30] if group.get('description') else ''
                    print(f"  • {group.get('displayName')} - {desc}")
            else:
                print(f"  {Colors.FAIL}Error fetching groups{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}Not authenticated{Colors.ENDC}")
    else:
        print(f"  {Colors.WARNING}requests module not available{Colors.ENDC}")
    
    print()

def cmd_config(args):
    """Configure credentials"""
    print(f"\n{Colors.BOLD}Configuration{Colors.ENDC}")
    print("=" * 50)
    
    if args.show:
        creds = load_credentials()
        print(f"\n{Colors.CYAN}Current Configuration:{Colors.ENDC}")
        print(f"  Azure Tenant ID: {creds.get('azure_tenant_id', 'Not set')[:20]}...")
        print(f"  Azure Client ID: {creds.get('azure_client_id', 'Not set')[:20]}...")
        print(f"  GHE Instance: {creds.get('ghe_instance_url', 'Not set')}")
        print(f"  Config Dir: {CONFIG_DIR}")
    elif args.init:
        print(f"\n{Colors.CYAN}Initializing configuration...{Colors.ENDC}")
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Create sample config
        sample_config = {
            "azure_tenant_id": "YOUR_TENANT_ID",
            "azure_client_id": "YOUR_CLIENT_ID",
            "azure_client_secret": "YOUR_CLIENT_SECRET",
            "ghe_instance_url": "https://zone.ghe.com",
            "ghe_admin_token": "YOUR_GHE_TOKEN"
        }
        
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(sample_config, f, indent=2)
        
        print(f"  Created: {CREDENTIALS_FILE}")
        print(f"  {Colors.WARNING}Please edit this file with your actual credentials{Colors.ENDC}")
    
    print()

def cmd_help(args):
    """Show help"""
    print_banner()
    print(f"""
{Colors.BOLD}Available Commands:{Colors.ENDC}

  {Colors.CYAN}status{Colors.ENDC}    Show connection status for Azure AD and GHE
  {Colors.CYAN}users{Colors.ENDC}     List users (--source azure|ghe|all)
  {Colors.CYAN}groups{Colors.ENDC}    List Azure AD groups
  {Colors.CYAN}config{Colors.ENDC}    Configure credentials (--show, --init)
  {Colors.CYAN}help{Colors.ENDC}      Show this help message

{Colors.BOLD}Examples:{Colors.ENDC}

  python3 beastmode.py status
  python3 beastmode.py users --source azure
  python3 beastmode.py config --init
  python3 beastmode.py config --show

{Colors.BOLD}Environment Variables:{Colors.ENDC}

  AZURE_TENANT_ID       Azure AD Tenant ID
  AZURE_CLIENT_ID       Azure AD Application Client ID
  AZURE_CLIENT_SECRET   Azure AD Application Client Secret
  GHE_INSTANCE_URL      GitHub Enterprise Instance URL
  GHE_ADMIN_TOKEN       GitHub Enterprise Admin Token

{Colors.BOLD}Documentation:{Colors.ENDC}

  See ~/beastmode/docs/ for detailed documentation.
""")

def main():
    parser = argparse.ArgumentParser(
        description='Beast Mode - MS Graph & GitHub Enterprise Automation Toolkit',
        add_help=False
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show connection status')
    status_parser.set_defaults(func=cmd_status)
    
    # Users command
    users_parser = subparsers.add_parser('users', help='List users')
    users_parser.add_argument('--source', choices=['azure', 'ghe', 'all'], default='all')
    users_parser.set_defaults(func=cmd_users)
    
    # Groups command
    groups_parser = subparsers.add_parser('groups', help='List groups')
    groups_parser.set_defaults(func=cmd_groups)
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure credentials')
    config_parser.add_argument('--show', action='store_true', help='Show current config')
    config_parser.add_argument('--init', action='store_true', help='Initialize config files')
    config_parser.set_defaults(func=cmd_config)
    
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
