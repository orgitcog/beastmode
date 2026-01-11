#!/usr/bin/env python3
"""
Organization Synchronization Toolkit
Synchronizes organizations, groups, and users between Azure AD and GitHub Enterprise

This toolkit provides functions to:
1. List and compare organizations/groups between Azure AD and GHE
2. Sync users from Azure AD groups to GHE teams
3. Create matching structures in both systems
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration for Azure AD and GitHub Enterprise"""
    
    # Azure AD / Microsoft Graph
    AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID')
    AZURE_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
    AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')
    
    # GitHub Enterprise
    GHE_INSTANCE_URL = os.environ.get('GHE_INSTANCE_URL', 'https://zone.ghe.com')
    GHE_ADMIN_TOKEN = os.environ.get('GHE_ADMIN_TOKEN')
    
    # Beast Mode credentials (if available)
    BEAST_MODE_FILE = '/home/ubuntu/beast_mode_credentials.json'
    
    @classmethod
    def load_beast_mode_creds(cls):
        """Load Beast Mode credentials if available"""
        if os.path.exists(cls.BEAST_MODE_FILE):
            with open(cls.BEAST_MODE_FILE, 'r') as f:
                creds = json.load(f)
                return creds
        return None

# ============================================================================
# AZURE AD CLIENT
# ============================================================================

class AzureADClient:
    """Client for Microsoft Graph API operations"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.base_url = "https://graph.microsoft.com/v1.0"
    
    def authenticate(self) -> bool:
        """Obtain access token"""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            self.token = response.json().get('access_token')
            return True
        return False
    
    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def get_organization(self) -> Optional[Dict]:
        """Get organization details"""
        response = requests.get(f"{self.base_url}/organization", headers=self._headers())
        if response.status_code == 200:
            return response.json().get('value', [{}])[0]
        return None
    
    def list_users(self, top: int = 999) -> List[Dict]:
        """List all users"""
        users = []
        url = f"{self.base_url}/users?$top={top}&$select=id,displayName,userPrincipalName,mail,jobTitle,department"
        
        while url:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                data = response.json()
                users.extend(data.get('value', []))
                url = data.get('@odata.nextLink')
            else:
                break
        
        return users
    
    def list_groups(self, top: int = 999) -> List[Dict]:
        """List all groups"""
        groups = []
        url = f"{self.base_url}/groups?$top={top}&$select=id,displayName,description,mail,groupTypes"
        
        while url:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                data = response.json()
                groups.extend(data.get('value', []))
                url = data.get('@odata.nextLink')
            else:
                break
        
        return groups
    
    def get_group_members(self, group_id: str) -> List[Dict]:
        """Get members of a group"""
        members = []
        url = f"{self.base_url}/groups/{group_id}/members?$select=id,displayName,userPrincipalName,mail"
        
        while url:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                data = response.json()
                members.extend(data.get('value', []))
                url = data.get('@odata.nextLink')
            else:
                break
        
        return members
    
    def create_group(self, display_name: str, description: str = "", mail_nickname: str = None) -> Optional[Dict]:
        """Create a new security group"""
        if not mail_nickname:
            mail_nickname = display_name.lower().replace(' ', '_')
        
        group_data = {
            "displayName": display_name,
            "description": description,
            "mailEnabled": False,
            "mailNickname": mail_nickname,
            "securityEnabled": True
        }
        
        response = requests.post(f"{self.base_url}/groups", headers=self._headers(), json=group_data)
        if response.status_code == 201:
            return response.json()
        return None
    
    def create_user(self, display_name: str, user_principal_name: str, password: str, 
                    mail_nickname: str = None, force_change_password: bool = True) -> Optional[Dict]:
        """Create a new user"""
        if not mail_nickname:
            mail_nickname = user_principal_name.split('@')[0]
        
        user_data = {
            "displayName": display_name,
            "mailNickname": mail_nickname,
            "userPrincipalName": user_principal_name,
            "accountEnabled": True,
            "passwordProfile": {
                "password": password,
                "forceChangePasswordNextSignIn": force_change_password
            }
        }
        
        response = requests.post(f"{self.base_url}/users", headers=self._headers(), json=user_data)
        if response.status_code == 201:
            return response.json()
        return None
    
    def add_group_member(self, group_id: str, user_id: str) -> bool:
        """Add a user to a group"""
        member_data = {
            "@odata.id": f"{self.base_url}/directoryObjects/{user_id}"
        }
        
        response = requests.post(
            f"{self.base_url}/groups/{group_id}/members/$ref",
            headers=self._headers(),
            json=member_data
        )
        return response.status_code in [200, 204]

# ============================================================================
# GITHUB ENTERPRISE CLIENT
# ============================================================================

class GitHubEnterpriseClient:
    """Client for GitHub Enterprise API operations"""
    
    def __init__(self, instance_url: str, token: str):
        self.instance_url = instance_url.rstrip('/')
        self.token = token
        self.base_url = f"{self.instance_url}/api/v3"
    
    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def list_organizations(self) -> List[Dict]:
        """List all organizations"""
        orgs = []
        url = f"{self.base_url}/organizations"
        
        while url:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                orgs.extend(response.json())
                # Check for pagination
                if 'next' in response.links:
                    url = response.links['next']['url']
                else:
                    url = None
            else:
                break
        
        return orgs
    
    def get_organization(self, org_name: str) -> Optional[Dict]:
        """Get organization details"""
        response = requests.get(f"{self.base_url}/orgs/{org_name}", headers=self._headers())
        if response.status_code == 200:
            return response.json()
        return None
    
    def list_org_members(self, org_name: str) -> List[Dict]:
        """List organization members"""
        members = []
        url = f"{self.base_url}/orgs/{org_name}/members"
        
        while url:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                members.extend(response.json())
                if 'next' in response.links:
                    url = response.links['next']['url']
                else:
                    url = None
            else:
                break
        
        return members
    
    def list_teams(self, org_name: str) -> List[Dict]:
        """List teams in an organization"""
        teams = []
        url = f"{self.base_url}/orgs/{org_name}/teams"
        
        while url:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                teams.extend(response.json())
                if 'next' in response.links:
                    url = response.links['next']['url']
                else:
                    url = None
            else:
                break
        
        return teams
    
    def get_team_members(self, org_name: str, team_slug: str) -> List[Dict]:
        """Get team members"""
        members = []
        url = f"{self.base_url}/orgs/{org_name}/teams/{team_slug}/members"
        
        while url:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                members.extend(response.json())
                if 'next' in response.links:
                    url = response.links['next']['url']
                else:
                    url = None
            else:
                break
        
        return members
    
    def create_team(self, org_name: str, team_name: str, description: str = "", 
                    privacy: str = "closed") -> Optional[Dict]:
        """Create a new team"""
        team_data = {
            "name": team_name,
            "description": description,
            "privacy": privacy
        }
        
        response = requests.post(
            f"{self.base_url}/orgs/{org_name}/teams",
            headers=self._headers(),
            json=team_data
        )
        if response.status_code == 201:
            return response.json()
        return None
    
    def add_team_member(self, org_name: str, team_slug: str, username: str, 
                        role: str = "member") -> bool:
        """Add a member to a team"""
        response = requests.put(
            f"{self.base_url}/orgs/{org_name}/teams/{team_slug}/memberships/{username}",
            headers=self._headers(),
            json={"role": role}
        )
        return response.status_code in [200, 201]

# ============================================================================
# SYNCHRONIZATION ENGINE
# ============================================================================

class OrgSyncEngine:
    """Engine for synchronizing organizations between Azure AD and GitHub Enterprise"""
    
    def __init__(self, azure_client: AzureADClient, ghe_client: GitHubEnterpriseClient):
        self.azure = azure_client
        self.ghe = ghe_client
        self.sync_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log a sync message"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        }
        self.sync_log.append(entry)
        print(f"[{level}] {message}")
    
    def compare_organizations(self) -> Dict:
        """Compare Azure AD groups with GHE organizations"""
        self.log("Comparing Azure AD groups with GHE organizations...")
        
        # Get Azure AD groups
        azure_groups = self.azure.list_groups()
        azure_group_names = {g['displayName'].lower(): g for g in azure_groups}
        
        # Get GHE organizations
        ghe_orgs = self.ghe.list_organizations()
        ghe_org_names = {o['login'].lower(): o for o in ghe_orgs}
        
        # Find matches and differences
        comparison = {
            "azure_only": [],
            "ghe_only": [],
            "matched": [],
            "azure_total": len(azure_groups),
            "ghe_total": len(ghe_orgs)
        }
        
        for name, group in azure_group_names.items():
            if name in ghe_org_names:
                comparison["matched"].append({
                    "name": name,
                    "azure_id": group['id'],
                    "ghe_id": ghe_org_names[name]['id']
                })
            else:
                comparison["azure_only"].append({
                    "name": group['displayName'],
                    "id": group['id']
                })
        
        for name, org in ghe_org_names.items():
            if name not in azure_group_names:
                comparison["ghe_only"].append({
                    "name": org['login'],
                    "id": org['id']
                })
        
        self.log(f"Comparison complete: {len(comparison['matched'])} matched, "
                 f"{len(comparison['azure_only'])} Azure-only, "
                 f"{len(comparison['ghe_only'])} GHE-only")
        
        return comparison
    
    def sync_group_to_team(self, azure_group_id: str, ghe_org: str, ghe_team_slug: str,
                           user_mapping: Dict[str, str]) -> Dict:
        """Sync Azure AD group members to a GHE team"""
        self.log(f"Syncing Azure AD group {azure_group_id} to GHE team {ghe_org}/{ghe_team_slug}")
        
        result = {
            "added": [],
            "skipped": [],
            "failed": [],
            "not_mapped": []
        }
        
        # Get Azure AD group members
        azure_members = self.azure.get_group_members(azure_group_id)
        
        for member in azure_members:
            email = member.get('mail') or member.get('userPrincipalName', '')
            
            # Look up GHE username from mapping
            ghe_username = user_mapping.get(email.lower())
            
            if not ghe_username:
                result["not_mapped"].append(email)
                continue
            
            # Add to GHE team
            success = self.ghe.add_team_member(ghe_org, ghe_team_slug, ghe_username)
            
            if success:
                result["added"].append(ghe_username)
                self.log(f"  Added {ghe_username} to {ghe_team_slug}")
            else:
                result["failed"].append(ghe_username)
                self.log(f"  Failed to add {ghe_username}", "ERROR")
        
        return result
    
    def generate_user_mapping(self, azure_users: List[Dict], ghe_members: List[Dict]) -> Dict[str, str]:
        """Generate a mapping between Azure AD users and GHE users based on email"""
        mapping = {}
        
        # Create a lookup of GHE users by email (if available) or login
        ghe_lookup = {}
        for member in ghe_members:
            login = member.get('login', '').lower()
            email = member.get('email', '').lower() if member.get('email') else None
            
            if email:
                ghe_lookup[email] = login
            ghe_lookup[login] = login
        
        # Map Azure users to GHE users
        for user in azure_users:
            azure_email = (user.get('mail') or user.get('userPrincipalName', '')).lower()
            azure_upn = user.get('userPrincipalName', '').lower()
            
            # Try to find a match
            if azure_email in ghe_lookup:
                mapping[azure_email] = ghe_lookup[azure_email]
            elif azure_upn.split('@')[0] in ghe_lookup:
                mapping[azure_email] = ghe_lookup[azure_upn.split('@')[0]]
        
        return mapping
    
    def export_sync_report(self, filepath: str):
        """Export sync log to a file"""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "log_entries": self.sync_log
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Sync report exported to {filepath}")

# ============================================================================
# MAIN DEMONSTRATION
# ============================================================================

def main():
    print("=" * 70)
    print("ORGANIZATION SYNCHRONIZATION TOOLKIT")
    print("=" * 70)
    print()
    
    # Initialize Azure AD client
    print("1. Initializing Azure AD client...")
    azure = AzureADClient(
        Config.AZURE_TENANT_ID,
        Config.AZURE_CLIENT_ID,
        Config.AZURE_CLIENT_SECRET
    )
    
    if azure.authenticate():
        print("   SUCCESS - Azure AD authenticated")
    else:
        print("   FAILED - Azure AD authentication failed")
        return
    
    # Initialize GHE client
    print("\n2. Initializing GitHub Enterprise client...")
    ghe = GitHubEnterpriseClient(
        Config.GHE_INSTANCE_URL,
        Config.GHE_ADMIN_TOKEN
    )
    
    # Test GHE connection
    orgs = ghe.list_organizations()
    print(f"   SUCCESS - Found {len(orgs)} GHE organizations")
    
    # Get Azure AD organization info
    print("\n3. Fetching Azure AD organization info...")
    org_info = azure.get_organization()
    if org_info:
        print(f"   Organization: {org_info.get('displayName')}")
    
    # List Azure AD groups
    print("\n4. Fetching Azure AD groups...")
    groups = azure.list_groups()
    print(f"   Found {len(groups)} groups")
    
    # List Azure AD users
    print("\n5. Fetching Azure AD users...")
    users = azure.list_users()
    print(f"   Found {len(users)} users")
    
    # Initialize sync engine
    print("\n6. Initializing sync engine...")
    sync = OrgSyncEngine(azure, ghe)
    
    # Compare organizations
    print("\n7. Comparing organizations...")
    comparison = sync.compare_organizations()
    
    print(f"\n   Azure AD Groups: {comparison['azure_total']}")
    print(f"   GHE Organizations: {comparison['ghe_total']}")
    print(f"   Matched: {len(comparison['matched'])}")
    print(f"   Azure-only: {len(comparison['azure_only'])}")
    print(f"   GHE-only: {len(comparison['ghe_only'])}")
    
    # Show matched organizations
    if comparison['matched']:
        print("\n   Matched Organizations:")
        for match in comparison['matched'][:5]:
            print(f"     • {match['name']}")
    
    # Show GHE organizations
    print("\n   GHE Organizations:")
    for org in orgs[:5]:
        print(f"     • {org.get('login')}")
    
    # Export comparison report
    report_path = '/home/ubuntu/org_sync_comparison.json'
    with open(report_path, 'w') as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "azure_org": org_info.get('displayName') if org_info else None,
            "comparison": comparison,
            "azure_groups_sample": [{"id": g["id"], "name": g["displayName"]} for g in groups[:20]],
            "ghe_orgs": [{"id": o["id"], "login": o["login"]} for o in orgs],
            "azure_users_count": len(users),
            "ghe_orgs_count": len(orgs)
        }, f, indent=2)
    
    print(f"\n   Comparison report saved to: {report_path}")
    
    print("\n" + "=" * 70)
    print("TOOLKIT READY")
    print("=" * 70)
    print("""
Available functions:
  - azure.list_users()         : List all Azure AD users
  - azure.list_groups()        : List all Azure AD groups
  - azure.get_group_members(id): Get members of a group
  - azure.create_group(name)   : Create a new group
  - azure.create_user(...)     : Create a new user
  
  - ghe.list_organizations()   : List all GHE organizations
  - ghe.list_teams(org)        : List teams in an organization
  - ghe.get_team_members(...)  : Get team members
  - ghe.create_team(...)       : Create a new team
  
  - sync.compare_organizations(): Compare Azure AD groups with GHE orgs
  - sync.sync_group_to_team(...): Sync group members to a team
""")

if __name__ == '__main__':
    main()
