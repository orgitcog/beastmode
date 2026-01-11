#!/usr/bin/env python3
"""
Script to create a "Beast Mode" Azure AD Application Registration
with comprehensive Microsoft Graph permissions for full directory management.

This script uses the existing Azure AD credentials to create a new app registration
with all necessary permissions for managing users, groups, teams, applications, etc.
"""

import os
import json
import requests
from datetime import datetime, timedelta

# Azure AD Credentials
TENANT_ID = os.environ.get('AZURE_TENANT_ID')
CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')

# Microsoft Graph App ID (constant)
MS_GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"

# Define the comprehensive permissions needed for "Beast Mode"
BEAST_MODE_PERMISSIONS = {
    # Core Directory Management
    "Directory.ReadWrite.All": "19dbc75e-c2e2-444c-a770-ec69d8559fc7",
    "User.ReadWrite.All": "741f803b-c850-494e-b5df-cde7c675a1ca",
    "Group.ReadWrite.All": "62a82d76-70ea-41e2-9197-370581804d09",
    "Application.ReadWrite.All": "1bfefb4e-e0b5-418b-a88f-73c46d2cc8e9",
    "AppRoleAssignment.ReadWrite.All": "06b708a9-e830-4db3-a914-8e69da51d44f",
    
    # Teams Management
    "Team.Create": "23fc2474-f741-46ce-8465-674744c5c361",
    "Team.ReadBasic.All": "2280dda6-0bfd-44ee-a2f4-cb867cfc4c1e",
    "TeamSettings.ReadWrite.All": "bdd80a03-d9bc-451d-b7c4-ce7c63fe3c8f",
    "Channel.Create": "f3a65bd4-b703-46df-8f7e-0174571a6a9d",
    "Channel.Delete.All": "6a118a39-1227-45d4-af0c-ea7b40d210bc",
    "ChannelMember.ReadWrite.All": "35930571-f7d6-4a72-a0e2-2d73d4b8f0b0",
    "TeamMember.ReadWrite.All": "0121dc95-1b9f-4aed-8bac-58c5ac466691",
    
    # Identity & Access Management
    "RoleManagement.ReadWrite.Directory": "9e3f62cf-ca93-4989-b6ce-bf83c28f9fe8",
    "Policy.ReadWrite.ConditionalAccess": "01c0a623-fc9b-48e9-b794-0756f8e8f067",
    "IdentityProvider.ReadWrite.All": "90db2b9a-d928-4d33-a4dd-8442ae3d41e4",
    "Organization.ReadWrite.All": "292d869f-3427-49a8-9dab-8c70152b74e9",
    
    # Administrative Units
    "AdministrativeUnit.ReadWrite.All": "5eb59dd3-1da2-4329-8733-9dabdc435916",
    
    # Domains
    "Domain.ReadWrite.All": "7e05723c-0bb0-42da-be95-ae9f08a6e53c",
    
    # Devices
    "Device.ReadWrite.All": "1138cb37-bd11-4084-a2b7-9f71582aeddb",
    
    # Audit & Reporting
    "AuditLog.Read.All": "b0afded3-3588-46d8-8b3d-9842eff778da",
    "Reports.Read.All": "230c1aed-a721-4c5d-9cb4-a90514e508ef",
    "Directory.Read.All": "7ab1d382-f21e-4acd-a863-ba3e13f7da61",
    
    # Mail (optional)
    "Mail.ReadWrite": "e2a3a72e-5f79-4c64-b1b1-878b674786c9",
    
    # Sites (SharePoint)
    "Sites.FullControl.All": "a82116e5-55eb-4c41-a434-62fe8a61c773",
    
    # Calendars
    "Calendars.ReadWrite": "ef54d2bf-783f-4e0f-bca1-3210c0444d99",
    
    # Service Principal Management
    "ServicePrincipalEndpoint.ReadWrite.All": "89c8469c-83ad-45f7-8ff2-6e3d4285709e",
}

def get_access_token():
    """Obtain access token using client credentials flow"""
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default',
        'grant_type': 'client_credentials'
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def get_graph_service_principal(token):
    """Get the Microsoft Graph service principal to retrieve permission IDs"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{MS_GRAPH_APP_ID}'"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('value'):
            return data['value'][0]
    return None

def create_application(token, app_name):
    """Create a new application registration"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Build the required resource access for Microsoft Graph
    resource_access = []
    for perm_name, perm_id in BEAST_MODE_PERMISSIONS.items():
        resource_access.append({
            "id": perm_id,
            "type": "Role"  # Application permission
        })
    
    app_data = {
        "displayName": app_name,
        "signInAudience": "AzureADMyOrg",
        "requiredResourceAccess": [
            {
                "resourceAppId": MS_GRAPH_APP_ID,
                "resourceAccess": resource_access
            }
        ]
    }
    
    url = "https://graph.microsoft.com/v1.0/applications"
    response = requests.post(url, headers=headers, json=app_data)
    
    return response

def create_service_principal(token, app_id):
    """Create a service principal for the application"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    sp_data = {
        "appId": app_id
    }
    
    url = "https://graph.microsoft.com/v1.0/servicePrincipals"
    response = requests.post(url, headers=headers, json=sp_data)
    
    return response

def add_client_secret(token, app_id):
    """Add a client secret to the application"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Secret valid for 2 years
    end_date = (datetime.utcnow() + timedelta(days=730)).isoformat() + "Z"
    
    secret_data = {
        "passwordCredential": {
            "displayName": "BeastModeSecret",
            "endDateTime": end_date
        }
    }
    
    url = f"https://graph.microsoft.com/v1.0/applications/{app_id}/addPassword"
    response = requests.post(url, headers=headers, json=secret_data)
    
    return response

def main():
    print("=" * 70)
    print("BEAST MODE APP REGISTRATION CREATOR")
    print("=" * 70)
    print()
    
    # Check credentials
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("ERROR: Missing Azure AD credentials!")
        return
    
    # Get access token
    print("1. Obtaining access token...")
    token = get_access_token()
    if not token:
        print("   FAILED to obtain access token!")
        return
    print("   SUCCESS")
    
    # Define the app name
    app_name = "OrgItCog-BeastMode"
    
    print(f"\n2. Creating application: {app_name}")
    print(f"   Permissions to be requested: {len(BEAST_MODE_PERMISSIONS)}")
    
    # Create the application
    response = create_application(token, app_name)
    
    if response.status_code == 201:
        app_data = response.json()
        app_object_id = app_data['id']
        app_client_id = app_data['appId']
        
        print(f"   SUCCESS - Application created!")
        print(f"   Object ID: {app_object_id}")
        print(f"   Application (Client) ID: {app_client_id}")
        
        # Create service principal
        print("\n3. Creating service principal...")
        sp_response = create_service_principal(token, app_client_id)
        
        if sp_response.status_code == 201:
            sp_data = sp_response.json()
            print(f"   SUCCESS - Service Principal ID: {sp_data['id']}")
        else:
            print(f"   WARNING: {sp_response.status_code} - {sp_response.text}")
        
        # Add client secret
        print("\n4. Adding client secret...")
        secret_response = add_client_secret(token, app_object_id)
        
        if secret_response.status_code == 200:
            secret_data = secret_response.json()
            client_secret = secret_data.get('secretText')
            
            print("   SUCCESS - Client secret created!")
            print()
            print("=" * 70)
            print("IMPORTANT: SAVE THESE CREDENTIALS SECURELY!")
            print("=" * 70)
            print(f"   Tenant ID:     {TENANT_ID}")
            print(f"   Client ID:     {app_client_id}")
            print(f"   Client Secret: {client_secret}")
            print(f"   Object ID:     {app_object_id}")
            print()
            print("=" * 70)
            print("NEXT STEPS:")
            print("=" * 70)
            print("   1. Go to Azure Portal > Microsoft Entra ID > App registrations")
            print(f"   2. Find '{app_name}' and open it")
            print("   3. Go to 'API permissions'")
            print("   4. Click 'Grant admin consent for [Your Org]'")
            print("   5. Confirm the consent")
            print()
            print("   After granting admin consent, the app will have full permissions.")
            
            # Save credentials to file
            creds = {
                "app_name": app_name,
                "tenant_id": TENANT_ID,
                "client_id": app_client_id,
                "client_secret": client_secret,
                "object_id": app_object_id,
                "permissions": list(BEAST_MODE_PERMISSIONS.keys()),
                "created_at": datetime.utcnow().isoformat()
            }
            
            with open('/home/ubuntu/beast_mode_credentials.json', 'w') as f:
                json.dump(creds, f, indent=2)
            
            print("\n   Credentials saved to: /home/ubuntu/beast_mode_credentials.json")
            
        else:
            print(f"   FAILED: {secret_response.status_code}")
            print(f"   {secret_response.text}")
    
    elif response.status_code == 400:
        error = response.json().get('error', {})
        print(f"   FAILED: {error.get('message', 'Unknown error')}")
    else:
        print(f"   FAILED: {response.status_code}")
        print(f"   {response.text}")
    
    # Print permission summary
    print()
    print("=" * 70)
    print("PERMISSIONS SUMMARY")
    print("=" * 70)
    
    categories = {
        "Directory": ["Directory.ReadWrite.All", "Directory.Read.All", "User.ReadWrite.All", "Group.ReadWrite.All"],
        "Applications": ["Application.ReadWrite.All", "AppRoleAssignment.ReadWrite.All", "ServicePrincipalEndpoint.ReadWrite.All"],
        "Teams": ["Team.Create", "Team.ReadBasic.All", "TeamSettings.ReadWrite.All", "Channel.Create", "Channel.Delete.All", "ChannelMember.ReadWrite.All", "TeamMember.ReadWrite.All"],
        "Identity": ["RoleManagement.ReadWrite.Directory", "Policy.ReadWrite.ConditionalAccess", "IdentityProvider.ReadWrite.All", "Organization.ReadWrite.All"],
        "Infrastructure": ["AdministrativeUnit.ReadWrite.All", "Domain.ReadWrite.All", "Device.ReadWrite.All"],
        "Audit": ["AuditLog.Read.All", "Reports.Read.All"],
        "Productivity": ["Mail.ReadWrite", "Sites.FullControl.All", "Calendars.ReadWrite"]
    }
    
    for category, perms in categories.items():
        print(f"\n{category}:")
        for p in perms:
            if p in BEAST_MODE_PERMISSIONS:
                print(f"   • {p}")

if __name__ == '__main__':
    main()
