#!/usr/bin/env python3
"""
Microsoft Graph SDK Helper Module

Provides a simplified interface for working with the Microsoft Graph SDK,
including authentication, common operations, and code generation helpers.

Usage:
    from graph_sdk import GraphClient
    
    client = GraphClient()
    users = client.get_users()
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

# Try to import the official SDK
try:
    from azure.identity import ClientSecretCredential
    from msgraph import GraphServiceClient
    from msgraph.generated.users.users_request_builder import UsersRequestBuilder
    HAS_SDK = True
except ImportError:
    HAS_SDK = False

# Fallback to requests-based implementation
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Configuration
CONFIG_DIR = Path.home() / ".beastmode"
CONFIG_FILE = CONFIG_DIR / "graph_config.json"

class GraphClient:
    """
    Microsoft Graph API Client
    
    Supports both the official SDK and a requests-based fallback.
    """
    
    def __init__(self, tenant_id: str = None, client_id: str = None, client_secret: str = None):
        """
        Initialize the Graph client.
        
        Args:
            tenant_id: Azure AD tenant ID (defaults to env var or config file)
            client_id: Azure AD application client ID
            client_secret: Azure AD application client secret
        """
        self.tenant_id = tenant_id or os.environ.get("AZURE_TENANT_ID") or self._load_config("tenant_id")
        self.client_id = client_id or os.environ.get("AZURE_CLIENT_ID") or self._load_config("client_id")
        self.client_secret = client_secret or os.environ.get("AZURE_CLIENT_SECRET") or self._load_config("client_secret")
        
        self._token = None
        self._sdk_client = None
        
        if HAS_SDK:
            self._init_sdk_client()
    
    def _load_config(self, key: str) -> Optional[str]:
        """Load a configuration value from the config file."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get(key)
        return None
    
    def _init_sdk_client(self):
        """Initialize the official SDK client."""
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            return
        
        try:
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self._sdk_client = GraphServiceClient(credential)
        except Exception as e:
            print(f"Warning: Could not initialize SDK client: {e}")
    
    def _get_token(self) -> Optional[str]:
        """Get an access token using client credentials flow."""
        if not HAS_REQUESTS:
            return None
        
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Missing Azure AD credentials")
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        
        response = requests.post(token_url, data=data, timeout=30)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make a request to the Graph API using requests library."""
        if not self._token:
            self._token = self._get_token()
        
        url = f"https://graph.microsoft.com/v1.0{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code >= 400:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        if response.status_code == 204:  # No content
            return {}
        
        return response.json()
    
    # User operations
    def get_users(self, top: int = 100, select: List[str] = None) -> List[Dict]:
        """Get a list of users."""
        params = {"$top": top}
        if select:
            params["$select"] = ",".join(select)
        
        result = self._make_request("GET", "/users", params=params)
        return result.get("value", [])
    
    def get_user(self, user_id: str, select: List[str] = None) -> Dict:
        """Get a specific user by ID or UPN."""
        params = {}
        if select:
            params["$select"] = ",".join(select)
        
        return self._make_request("GET", f"/users/{user_id}", params=params)
    
    def create_user(self, user_data: Dict) -> Dict:
        """Create a new user."""
        return self._make_request("POST", "/users", data=user_data)
    
    def update_user(self, user_id: str, user_data: Dict) -> Dict:
        """Update a user."""
        return self._make_request("PATCH", f"/users/{user_id}", data=user_data)
    
    def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        self._make_request("DELETE", f"/users/{user_id}")
    
    # Group operations
    def get_groups(self, top: int = 100, select: List[str] = None) -> List[Dict]:
        """Get a list of groups."""
        params = {"$top": top}
        if select:
            params["$select"] = ",".join(select)
        
        result = self._make_request("GET", "/groups", params=params)
        return result.get("value", [])
    
    def get_group(self, group_id: str, select: List[str] = None) -> Dict:
        """Get a specific group by ID."""
        params = {}
        if select:
            params["$select"] = ",".join(select)
        
        return self._make_request("GET", f"/groups/{group_id}", params=params)
    
    def create_group(self, group_data: Dict) -> Dict:
        """Create a new group."""
        return self._make_request("POST", "/groups", data=group_data)
    
    def get_group_members(self, group_id: str) -> List[Dict]:
        """Get members of a group."""
        result = self._make_request("GET", f"/groups/{group_id}/members")
        return result.get("value", [])
    
    def add_group_member(self, group_id: str, member_id: str) -> None:
        """Add a member to a group."""
        data = {
            "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{member_id}"
        }
        self._make_request("POST", f"/groups/{group_id}/members/$ref", data=data)
    
    # Application operations
    def get_applications(self, top: int = 100) -> List[Dict]:
        """Get a list of applications."""
        params = {"$top": top}
        result = self._make_request("GET", "/applications", params=params)
        return result.get("value", [])
    
    def get_application(self, app_id: str) -> Dict:
        """Get a specific application by ID."""
        return self._make_request("GET", f"/applications/{app_id}")
    
    def create_application(self, app_data: Dict) -> Dict:
        """Create a new application."""
        return self._make_request("POST", "/applications", data=app_data)
    
    # Organization operations
    def get_organization(self) -> Dict:
        """Get organization details."""
        result = self._make_request("GET", "/organization")
        orgs = result.get("value", [])
        return orgs[0] if orgs else {}
    
    # Service Principal operations
    def get_service_principals(self, top: int = 100) -> List[Dict]:
        """Get a list of service principals."""
        params = {"$top": top}
        result = self._make_request("GET", "/servicePrincipals", params=params)
        return result.get("value", [])
    
    # Directory roles
    def get_directory_roles(self) -> List[Dict]:
        """Get a list of directory roles."""
        result = self._make_request("GET", "/directoryRoles")
        return result.get("value", [])
    
    # Teams operations
    def get_teams(self, top: int = 100) -> List[Dict]:
        """Get a list of teams."""
        params = {"$top": top}
        result = self._make_request("GET", "/teams", params=params)
        return result.get("value", [])
    
    # Generic request method
    def request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make a generic request to the Graph API."""
        return self._make_request(method, endpoint, data=data, params=params)


class CodeGenerator:
    """
    Generate code snippets for Microsoft Graph API operations.
    """
    
    @staticmethod
    def generate_python(method: str, endpoint: str, body: Dict = None) -> str:
        """Generate Python code for a Graph API request."""
        code = f'''import requests

# Configuration
TENANT_ID = "your-tenant-id"
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"

# Get access token
token_url = f"https://login.microsoftonline.com/{{TENANT_ID}}/oauth2/v2.0/token"
token_data = {{
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "https://graph.microsoft.com/.default",
    "grant_type": "client_credentials"
}}
token_response = requests.post(token_url, data=token_data)
access_token = token_response.json()["access_token"]

# Make Graph API request
headers = {{
    "Authorization": f"Bearer {{access_token}}",
    "Content-Type": "application/json"
}}

url = "https://graph.microsoft.com/v1.0{endpoint}"
'''
        
        if method.upper() == "GET":
            code += f'response = requests.get(url, headers=headers)\n'
        elif method.upper() == "POST":
            body_str = json.dumps(body, indent=4) if body else "{}"
            code += f'''body = {body_str}
response = requests.post(url, headers=headers, json=body)
'''
        elif method.upper() == "PATCH":
            body_str = json.dumps(body, indent=4) if body else "{}"
            code += f'''body = {body_str}
response = requests.patch(url, headers=headers, json=body)
'''
        elif method.upper() == "DELETE":
            code += f'response = requests.delete(url, headers=headers)\n'
        
        code += '''
# Handle response
if response.status_code < 400:
    print("Success!")
    if response.text:
        print(response.json())
else:
    print(f"Error: {response.status_code}")
    print(response.text)
'''
        return code
    
    @staticmethod
    def generate_powershell(method: str, endpoint: str, body: Dict = None) -> str:
        """Generate PowerShell code for a Graph API request."""
        code = f'''# Connect to Microsoft Graph
Connect-MgGraph -TenantId "your-tenant-id" -ClientId "your-client-id" -ClientSecretCredential $credential

# Make Graph API request
$uri = "https://graph.microsoft.com/v1.0{endpoint}"
'''
        
        if method.upper() == "GET":
            code += f'$response = Invoke-MgGraphRequest -Method GET -Uri $uri\n'
        elif method.upper() == "POST":
            body_str = json.dumps(body, indent=4) if body else "{}"
            code += f'''$body = @'
{body_str}
'@
$response = Invoke-MgGraphRequest -Method POST -Uri $uri -Body $body -ContentType "application/json"
'''
        elif method.upper() == "PATCH":
            body_str = json.dumps(body, indent=4) if body else "{}"
            code += f'''$body = @'
{body_str}
'@
$response = Invoke-MgGraphRequest -Method PATCH -Uri $uri -Body $body -ContentType "application/json"
'''
        elif method.upper() == "DELETE":
            code += f'$response = Invoke-MgGraphRequest -Method DELETE -Uri $uri\n'
        
        code += '''
# Display response
$response | ConvertTo-Json -Depth 10
'''
        return code
    
    @staticmethod
    def generate_curl(method: str, endpoint: str, body: Dict = None) -> str:
        """Generate cURL command for a Graph API request."""
        cmd = f'''# First, get an access token
TOKEN=$(curl -s -X POST \\
  "https://login.microsoftonline.com/YOUR_TENANT_ID/oauth2/v2.0/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "client_id=YOUR_CLIENT_ID" \\
  -d "client_secret=YOUR_CLIENT_SECRET" \\
  -d "scope=https://graph.microsoft.com/.default" \\
  -d "grant_type=client_credentials" | jq -r '.access_token')

# Make the Graph API request
curl -X {method.upper()} \\
  "https://graph.microsoft.com/v1.0{endpoint}" \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json"'''
        
        if body and method.upper() in ["POST", "PATCH", "PUT"]:
            body_str = json.dumps(body)
            cmd += f" \\\n  -d '{body_str}'"
        
        return cmd


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Microsoft Graph SDK Helper")
    parser.add_argument("--test", action="store_true", help="Test the SDK connection")
    parser.add_argument("--generate", choices=["python", "powershell", "curl"], help="Generate code snippet")
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--endpoint", default="/users", help="Graph API endpoint")
    
    args = parser.parse_args()
    
    if args.test:
        print("Testing Microsoft Graph SDK connection...")
        try:
            client = GraphClient()
            org = client.get_organization()
            print(f"✓ Connected to: {org.get('displayName', 'Unknown')}")
            print(f"  Tenant ID: {org.get('id', 'Unknown')}")
        except Exception as e:
            print(f"✗ Connection failed: {e}")
    
    elif args.generate:
        generator = CodeGenerator()
        if args.generate == "python":
            print(generator.generate_python(args.method, args.endpoint))
        elif args.generate == "powershell":
            print(generator.generate_powershell(args.method, args.endpoint))
        elif args.generate == "curl":
            print(generator.generate_curl(args.method, args.endpoint))
    
    else:
        print("Microsoft Graph SDK Helper")
        print("Use --test to test connection or --generate to generate code snippets")
        print(f"SDK Available: {HAS_SDK}")
        print(f"Requests Available: {HAS_REQUESTS}")
