#!/usr/bin/env python3
"""
Graph Explorer CLI - Terminal-based Microsoft Graph API Explorer

A command-line interface for exploring and testing Microsoft Graph API endpoints,
similar to the web-based Graph Explorer but optimized for terminal use.

Usage:
    python3 graph_explorer.py [command] [options]

Commands:
    auth        - Authenticate with Azure AD
    get         - Make a GET request to Graph API
    post        - Make a POST request to Graph API
    patch       - Make a PATCH request to Graph API
    delete      - Make a DELETE request to Graph API
    me          - Get current user profile
    users       - List users
    groups      - List groups
    apps        - List applications
    history     - Show request history
    endpoints   - List common endpoints
    interactive - Start interactive mode
"""

import os
import sys
import json
import argparse
import readline
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.markdown import Markdown
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Configuration
CONFIG_DIR = Path.home() / ".beastmode"
CONFIG_FILE = CONFIG_DIR / "graph_config.json"
HISTORY_FILE = CONFIG_DIR / "graph_history.json"
TOKEN_CACHE = CONFIG_DIR / "token_cache.json"

# Graph API endpoints
GRAPH_ENDPOINT = "https://graph.microsoft.com"
GRAPH_VERSION = "v1.0"

# Common endpoints for quick access
COMMON_ENDPOINTS = {
    "me": "/me",
    "me/photo": "/me/photo/$value",
    "me/messages": "/me/messages",
    "me/calendar": "/me/calendar",
    "me/drive": "/me/drive",
    "me/contacts": "/me/contacts",
    "users": "/users",
    "groups": "/groups",
    "applications": "/applications",
    "servicePrincipals": "/servicePrincipals",
    "organization": "/organization",
    "domains": "/domains",
    "directoryRoles": "/directoryRoles",
    "teams": "/teams",
    "sites": "/sites",
    "places": "/places",
    "devices": "/devices",
    "auditLogs/signIns": "/auditLogs/signIns",
    "auditLogs/directoryAudits": "/auditLogs/directoryAudits",
    "identityGovernance": "/identityGovernance",
    "policies": "/policies",
    "security/alerts": "/security/alerts",
}

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
    """Print the Graph Explorer banner"""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════╗
║  {Colors.BOLD}Microsoft Graph Explorer CLI{Colors.CYAN}                                    ║
║  {Colors.DIM}Terminal-based Graph API Explorer for Beast Mode{Colors.CYAN}                ║
╚══════════════════════════════════════════════════════════════════╝{Colors.ENDC}
"""
    print(banner)

def load_config():
    """Load configuration from file"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "tenant_id": os.environ.get("AZURE_TENANT_ID", ""),
        "client_id": os.environ.get("AZURE_CLIENT_ID", ""),
        "client_secret": os.environ.get("AZURE_CLIENT_SECRET", ""),
        "scopes": ["https://graph.microsoft.com/.default"]
    }

def save_config(config):
    """Save configuration to file"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_token_cache():
    """Load cached token"""
    if TOKEN_CACHE.exists():
        with open(TOKEN_CACHE, 'r') as f:
            cache = json.load(f)
            if cache.get("expires_at", 0) > time.time():
                return cache.get("access_token")
    return None

def save_token_cache(token, expires_in):
    """Save token to cache"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cache = {
        "access_token": token,
        "expires_at": time.time() + expires_in - 60  # 60 second buffer
    }
    with open(TOKEN_CACHE, 'w') as f:
        json.dump(cache, f)

def load_history():
    """Load request history"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    """Save request history"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Keep only last 100 entries
    history = history[-100:]
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def add_to_history(method, endpoint, status_code, response_time):
    """Add a request to history"""
    history = load_history()
    history.append({
        "timestamp": datetime.now().isoformat(),
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time_ms": response_time
    })
    save_history(history)

def get_access_token(config):
    """Get access token using client credentials flow"""
    if not HAS_REQUESTS:
        print(f"{Colors.RED}Error: requests library not available{Colors.ENDC}")
        return None
    
    # Check cache first
    cached_token = load_token_cache()
    if cached_token:
        return cached_token
    
    tenant_id = config.get("tenant_id") or os.environ.get("AZURE_TENANT_ID")
    client_id = config.get("client_id") or os.environ.get("AZURE_CLIENT_ID")
    client_secret = config.get("client_secret") or os.environ.get("AZURE_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        print(f"{Colors.RED}Error: Missing Azure AD credentials{Colors.ENDC}")
        print(f"Please set AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET")
        print(f"Or run: graph_explorer.py config --init")
        return None
    
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            save_token_cache(access_token, expires_in)
            return access_token
        else:
            print(f"{Colors.RED}Authentication failed: {response.status_code}{Colors.ENDC}")
            print(response.text)
            return None
    except Exception as e:
        print(f"{Colors.RED}Authentication error: {e}{Colors.ENDC}")
        return None

def make_graph_request(method, endpoint, token, data=None, params=None):
    """Make a request to Microsoft Graph API"""
    if not HAS_REQUESTS:
        return None, 0, "requests library not available"
    
    url = f"{GRAPH_ENDPOINT}/{GRAPH_VERSION}{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        else:
            return None, 0, f"Unsupported method: {method}"
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Add to history
        add_to_history(method.upper(), endpoint, response.status_code, response_time)
        
        return response, response_time, None
        
    except Exception as e:
        return None, 0, str(e)

def format_response(response, response_time):
    """Format and display the API response"""
    status_color = Colors.GREEN if response.status_code < 400 else Colors.RED
    
    print(f"\n{Colors.BOLD}Response:{Colors.ENDC}")
    print(f"  Status: {status_color}{response.status_code} {response.reason}{Colors.ENDC}")
    print(f"  Time: {response_time}ms")
    
    # Try to parse as JSON
    try:
        data = response.json()
        
        if HAS_RICH:
            console = Console()
            json_str = json.dumps(data, indent=2)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            print(f"\n{Colors.CYAN}Body:{Colors.ENDC}")
            print(json.dumps(data, indent=2))
            
        return data
    except:
        print(f"\n{Colors.CYAN}Body:{Colors.ENDC}")
        print(response.text[:1000])
        return None

def cmd_auth(args):
    """Test authentication"""
    print(f"\n{Colors.BOLD}Testing Authentication...{Colors.ENDC}")
    
    config = load_config()
    token = get_access_token(config)
    
    if token:
        print(f"{Colors.GREEN}✓ Authentication successful{Colors.ENDC}")
        print(f"  Token: {token[:20]}...{token[-10:]}")
        
        # Test with a simple request
        response, response_time, error = make_graph_request("GET", "/organization", token)
        if response and response.status_code == 200:
            org_data = response.json()
            if org_data.get("value"):
                org = org_data["value"][0]
                print(f"  Organization: {org.get('displayName', 'N/A')}")
                print(f"  Tenant ID: {org.get('id', 'N/A')}")
    else:
        print(f"{Colors.RED}✗ Authentication failed{Colors.ENDC}")

def cmd_get(args):
    """Make a GET request"""
    config = load_config()
    token = get_access_token(config)
    
    if not token:
        return
    
    endpoint = args.endpoint
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    
    # Handle query parameters
    params = {}
    if args.select:
        params["$select"] = args.select
    if args.filter:
        params["$filter"] = args.filter
    if args.top:
        params["$top"] = args.top
    if args.orderby:
        params["$orderby"] = args.orderby
    if args.expand:
        params["$expand"] = args.expand
    
    print(f"\n{Colors.CYAN}GET {GRAPH_ENDPOINT}/{GRAPH_VERSION}{endpoint}{Colors.ENDC}")
    if params:
        print(f"  Query: {params}")
    
    response, response_time, error = make_graph_request("GET", endpoint, token, params=params)
    
    if error:
        print(f"{Colors.RED}Error: {error}{Colors.ENDC}")
    elif response:
        format_response(response, response_time)

def cmd_post(args):
    """Make a POST request"""
    config = load_config()
    token = get_access_token(config)
    
    if not token:
        return
    
    endpoint = args.endpoint
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    
    # Parse body
    body = None
    if args.body:
        try:
            body = json.loads(args.body)
        except json.JSONDecodeError:
            print(f"{Colors.RED}Error: Invalid JSON body{Colors.ENDC}")
            return
    elif args.body_file:
        try:
            with open(args.body_file, 'r') as f:
                body = json.load(f)
        except Exception as e:
            print(f"{Colors.RED}Error reading body file: {e}{Colors.ENDC}")
            return
    
    print(f"\n{Colors.CYAN}POST {GRAPH_ENDPOINT}/{GRAPH_VERSION}{endpoint}{Colors.ENDC}")
    if body:
        print(f"  Body: {json.dumps(body)[:100]}...")
    
    response, response_time, error = make_graph_request("POST", endpoint, token, data=body)
    
    if error:
        print(f"{Colors.RED}Error: {error}{Colors.ENDC}")
    elif response:
        format_response(response, response_time)

def cmd_me(args):
    """Get current user (requires delegated permissions)"""
    config = load_config()
    token = get_access_token(config)
    
    if not token:
        return
    
    print(f"\n{Colors.CYAN}GET /me{Colors.ENDC}")
    print(f"{Colors.YELLOW}Note: /me endpoint requires delegated permissions (user context){Colors.ENDC}")
    print(f"With application permissions, use /users/{{user-id}} instead\n")
    
    response, response_time, error = make_graph_request("GET", "/me", token)
    
    if error:
        print(f"{Colors.RED}Error: {error}{Colors.ENDC}")
    elif response:
        format_response(response, response_time)

def cmd_users(args):
    """List users"""
    config = load_config()
    token = get_access_token(config)
    
    if not token:
        return
    
    params = {"$top": args.top or 10}
    if args.select:
        params["$select"] = args.select
    else:
        params["$select"] = "id,displayName,userPrincipalName,mail,jobTitle"
    
    print(f"\n{Colors.CYAN}GET /users{Colors.ENDC}")
    
    response, response_time, error = make_graph_request("GET", "/users", token, params=params)
    
    if error:
        print(f"{Colors.RED}Error: {error}{Colors.ENDC}")
    elif response and response.status_code == 200:
        data = response.json()
        users = data.get("value", [])
        
        if HAS_RICH:
            console = Console()
            table = Table(title=f"Users ({len(users)} results)")
            table.add_column("Display Name", style="cyan")
            table.add_column("UPN", style="green")
            table.add_column("Job Title")
            
            for user in users:
                table.add_row(
                    user.get("displayName", "N/A"),
                    user.get("userPrincipalName", "N/A"),
                    user.get("jobTitle", "N/A")
                )
            console.print(table)
        else:
            print(f"\n{Colors.BOLD}Users ({len(users)} results):{Colors.ENDC}")
            for user in users:
                print(f"  • {user.get('displayName', 'N/A')} ({user.get('userPrincipalName', 'N/A')})")
    else:
        format_response(response, response_time)

def cmd_groups(args):
    """List groups"""
    config = load_config()
    token = get_access_token(config)
    
    if not token:
        return
    
    params = {"$top": args.top or 10}
    if args.select:
        params["$select"] = args.select
    else:
        params["$select"] = "id,displayName,description,groupTypes,membershipRule"
    
    print(f"\n{Colors.CYAN}GET /groups{Colors.ENDC}")
    
    response, response_time, error = make_graph_request("GET", "/groups", token, params=params)
    
    if error:
        print(f"{Colors.RED}Error: {error}{Colors.ENDC}")
    elif response and response.status_code == 200:
        data = response.json()
        groups = data.get("value", [])
        
        if HAS_RICH:
            console = Console()
            table = Table(title=f"Groups ({len(groups)} results)")
            table.add_column("Display Name", style="cyan")
            table.add_column("Description")
            table.add_column("Type")
            
            for group in groups:
                group_types = group.get("groupTypes", [])
                group_type = "Unified" if "Unified" in group_types else "Security"
                table.add_row(
                    group.get("displayName", "N/A"),
                    (group.get("description", "N/A") or "N/A")[:40],
                    group_type
                )
            console.print(table)
        else:
            print(f"\n{Colors.BOLD}Groups ({len(groups)} results):{Colors.ENDC}")
            for group in groups:
                print(f"  • {group.get('displayName', 'N/A')}")
    else:
        format_response(response, response_time)

def cmd_apps(args):
    """List applications"""
    config = load_config()
    token = get_access_token(config)
    
    if not token:
        return
    
    params = {"$top": args.top or 10}
    params["$select"] = "id,displayName,appId,createdDateTime"
    
    print(f"\n{Colors.CYAN}GET /applications{Colors.ENDC}")
    
    response, response_time, error = make_graph_request("GET", "/applications", token, params=params)
    
    if error:
        print(f"{Colors.RED}Error: {error}{Colors.ENDC}")
    elif response and response.status_code == 200:
        data = response.json()
        apps = data.get("value", [])
        
        if HAS_RICH:
            console = Console()
            table = Table(title=f"Applications ({len(apps)} results)")
            table.add_column("Display Name", style="cyan")
            table.add_column("App ID", style="green")
            table.add_column("Created")
            
            for app in apps:
                table.add_row(
                    app.get("displayName", "N/A"),
                    app.get("appId", "N/A")[:20] + "...",
                    app.get("createdDateTime", "N/A")[:10]
                )
            console.print(table)
        else:
            print(f"\n{Colors.BOLD}Applications ({len(apps)} results):{Colors.ENDC}")
            for app in apps:
                print(f"  • {app.get('displayName', 'N/A')} ({app.get('appId', 'N/A')[:20]}...)")
    else:
        format_response(response, response_time)

def cmd_endpoints(args):
    """List common endpoints"""
    print(f"\n{Colors.BOLD}Common Microsoft Graph Endpoints:{Colors.ENDC}\n")
    
    if HAS_RICH:
        console = Console()
        table = Table(title="Common Endpoints")
        table.add_column("Shortcut", style="cyan")
        table.add_column("Endpoint", style="green")
        
        for name, endpoint in sorted(COMMON_ENDPOINTS.items()):
            table.add_row(name, endpoint)
        console.print(table)
    else:
        for name, endpoint in sorted(COMMON_ENDPOINTS.items()):
            print(f"  {Colors.CYAN}{name:30}{Colors.ENDC} → {endpoint}")
    
    print(f"\n{Colors.DIM}Use: graph_explorer.py get <endpoint>{Colors.ENDC}")

def cmd_history(args):
    """Show request history"""
    history = load_history()
    
    if not history:
        print(f"\n{Colors.YELLOW}No request history found{Colors.ENDC}")
        return
    
    print(f"\n{Colors.BOLD}Request History (last {min(len(history), 20)} requests):{Colors.ENDC}\n")
    
    if HAS_RICH:
        console = Console()
        table = Table(title="Request History")
        table.add_column("Time", style="dim")
        table.add_column("Method", style="cyan")
        table.add_column("Endpoint")
        table.add_column("Status")
        table.add_column("Time (ms)")
        
        for entry in history[-20:]:
            status_style = "green" if entry["status_code"] < 400 else "red"
            table.add_row(
                entry["timestamp"][11:19],
                entry["method"],
                entry["endpoint"][:40],
                f"[{status_style}]{entry['status_code']}[/{status_style}]",
                str(entry["response_time_ms"])
            )
        console.print(table)
    else:
        for entry in history[-20:]:
            status_color = Colors.GREEN if entry["status_code"] < 400 else Colors.RED
            print(f"  {entry['timestamp'][11:19]} {entry['method']:6} {status_color}{entry['status_code']}{Colors.ENDC} {entry['endpoint'][:50]}")

def cmd_config(args):
    """Configure Graph Explorer"""
    if args.init:
        print(f"\n{Colors.BOLD}Initializing Graph Explorer configuration...{Colors.ENDC}")
        
        config = {
            "tenant_id": input("Azure Tenant ID: ").strip() or os.environ.get("AZURE_TENANT_ID", ""),
            "client_id": input("Azure Client ID: ").strip() or os.environ.get("AZURE_CLIENT_ID", ""),
            "client_secret": input("Azure Client Secret: ").strip() or os.environ.get("AZURE_CLIENT_SECRET", ""),
            "scopes": ["https://graph.microsoft.com/.default"]
        }
        
        save_config(config)
        print(f"\n{Colors.GREEN}✓ Configuration saved to {CONFIG_FILE}{Colors.ENDC}")
        
    elif args.show:
        config = load_config()
        print(f"\n{Colors.BOLD}Current Configuration:{Colors.ENDC}")
        print(f"  Tenant ID: {config.get('tenant_id', 'Not set')[:20]}...")
        print(f"  Client ID: {config.get('client_id', 'Not set')[:20]}...")
        print(f"  Config File: {CONFIG_FILE}")
        
    elif args.clear_cache:
        if TOKEN_CACHE.exists():
            TOKEN_CACHE.unlink()
            print(f"{Colors.GREEN}✓ Token cache cleared{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}No token cache found{Colors.ENDC}")

def cmd_interactive(args):
    """Start interactive mode"""
    print_banner()
    print(f"{Colors.DIM}Type 'help' for commands, 'quit' to exit{Colors.ENDC}\n")
    
    config = load_config()
    token = get_access_token(config)
    
    if not token:
        print(f"{Colors.RED}Warning: Not authenticated. Run 'auth' to authenticate.{Colors.ENDC}\n")
    
    while True:
        try:
            cmd = input(f"{Colors.CYAN}graph>{Colors.ENDC} ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split()
            command = parts[0].lower()
            
            if command in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            elif command == "help":
                print(f"""
{Colors.BOLD}Commands:{Colors.ENDC}
  GET <endpoint>     - Make a GET request
  POST <endpoint>    - Make a POST request (prompts for body)
  users              - List users
  groups             - List groups
  apps               - List applications
  endpoints          - Show common endpoints
  history            - Show request history
  auth               - Test authentication
  clear              - Clear screen
  quit               - Exit interactive mode
""")
            elif command == "get" and len(parts) > 1:
                endpoint = parts[1]
                if not endpoint.startswith("/"):
                    endpoint = "/" + endpoint
                response, response_time, error = make_graph_request("GET", endpoint, token)
                if error:
                    print(f"{Colors.RED}Error: {error}{Colors.ENDC}")
                elif response:
                    format_response(response, response_time)
            elif command == "users":
                cmd_users(argparse.Namespace(top=10, select=None))
            elif command == "groups":
                cmd_groups(argparse.Namespace(top=10, select=None))
            elif command == "apps":
                cmd_apps(argparse.Namespace(top=10))
            elif command == "endpoints":
                cmd_endpoints(None)
            elif command == "history":
                cmd_history(None)
            elif command == "auth":
                token = get_access_token(config)
                if token:
                    print(f"{Colors.GREEN}✓ Authenticated{Colors.ENDC}")
            elif command == "clear":
                os.system('clear')
            else:
                print(f"{Colors.YELLOW}Unknown command: {command}{Colors.ENDC}")
                
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except EOFError:
            break

def cmd_help(args):
    """Show help"""
    print_banner()
    print(f"""
{Colors.BOLD}Usage:{Colors.ENDC}
  graph_explorer.py <command> [options]

{Colors.BOLD}Commands:{Colors.ENDC}
  {Colors.CYAN}auth{Colors.ENDC}         Test authentication with Azure AD
  {Colors.CYAN}get{Colors.ENDC}          Make a GET request to Graph API
  {Colors.CYAN}post{Colors.ENDC}         Make a POST request to Graph API
  {Colors.CYAN}me{Colors.ENDC}           Get current user profile
  {Colors.CYAN}users{Colors.ENDC}        List users
  {Colors.CYAN}groups{Colors.ENDC}       List groups
  {Colors.CYAN}apps{Colors.ENDC}         List applications
  {Colors.CYAN}endpoints{Colors.ENDC}    List common Graph API endpoints
  {Colors.CYAN}history{Colors.ENDC}      Show request history
  {Colors.CYAN}config{Colors.ENDC}       Configure credentials (--init, --show, --clear-cache)
  {Colors.CYAN}interactive{Colors.ENDC}  Start interactive mode

{Colors.BOLD}Examples:{Colors.ENDC}
  graph_explorer.py auth
  graph_explorer.py get /users --top 5
  graph_explorer.py get /groups --select displayName,id
  graph_explorer.py users --top 20
  graph_explorer.py interactive

{Colors.BOLD}Environment Variables:{Colors.ENDC}
  AZURE_TENANT_ID       Azure AD Tenant ID
  AZURE_CLIENT_ID       Azure AD Application Client ID
  AZURE_CLIENT_SECRET   Azure AD Application Client Secret
""")

def main():
    parser = argparse.ArgumentParser(
        description='Graph Explorer CLI - Terminal-based Microsoft Graph API Explorer',
        add_help=False
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Auth command
    auth_parser = subparsers.add_parser('auth', help='Test authentication')
    auth_parser.set_defaults(func=cmd_auth)
    
    # GET command
    get_parser = subparsers.add_parser('get', help='Make a GET request')
    get_parser.add_argument('endpoint', help='Graph API endpoint')
    get_parser.add_argument('--select', help='$select query parameter')
    get_parser.add_argument('--filter', help='$filter query parameter')
    get_parser.add_argument('--top', type=int, help='$top query parameter')
    get_parser.add_argument('--orderby', help='$orderby query parameter')
    get_parser.add_argument('--expand', help='$expand query parameter')
    get_parser.set_defaults(func=cmd_get)
    
    # POST command
    post_parser = subparsers.add_parser('post', help='Make a POST request')
    post_parser.add_argument('endpoint', help='Graph API endpoint')
    post_parser.add_argument('--body', help='JSON body')
    post_parser.add_argument('--body-file', help='Path to JSON file for body')
    post_parser.set_defaults(func=cmd_post)
    
    # Me command
    me_parser = subparsers.add_parser('me', help='Get current user')
    me_parser.set_defaults(func=cmd_me)
    
    # Users command
    users_parser = subparsers.add_parser('users', help='List users')
    users_parser.add_argument('--top', type=int, help='Number of results')
    users_parser.add_argument('--select', help='Properties to select')
    users_parser.set_defaults(func=cmd_users)
    
    # Groups command
    groups_parser = subparsers.add_parser('groups', help='List groups')
    groups_parser.add_argument('--top', type=int, help='Number of results')
    groups_parser.add_argument('--select', help='Properties to select')
    groups_parser.set_defaults(func=cmd_groups)
    
    # Apps command
    apps_parser = subparsers.add_parser('apps', help='List applications')
    apps_parser.add_argument('--top', type=int, help='Number of results')
    apps_parser.set_defaults(func=cmd_apps)
    
    # Endpoints command
    endpoints_parser = subparsers.add_parser('endpoints', help='List common endpoints')
    endpoints_parser.set_defaults(func=cmd_endpoints)
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show request history')
    history_parser.set_defaults(func=cmd_history)
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure credentials')
    config_parser.add_argument('--init', action='store_true', help='Initialize configuration')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--clear-cache', action='store_true', help='Clear token cache')
    config_parser.set_defaults(func=cmd_config)
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Start interactive mode')
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
