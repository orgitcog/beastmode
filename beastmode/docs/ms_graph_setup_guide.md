# Microsoft Graph PowerShell and Azure Cloud Shell Setup Guide

**Author:** Manus AI
**Date:** 2026-01-09

## 1. Introduction

This guide provides instructions for setting up and using the Microsoft Graph PowerShell SDK and Azure Cloud Shell to manage your Microsoft 365 and Azure Active Directory (Azure AD) environment. Following this guide will enable you to perform administrative tasks, automate processes, and manage resources programmatically.

## 2. Setting up Microsoft Graph PowerShell SDK

The Microsoft Graph PowerShell SDK allows you to call the Microsoft Graph API from PowerShell. It provides a rich set of cmdlets to manage your directory.

### 2.1. Installation

1.  **Set Execution Policy**: Ensure your execution policy allows running scripts. Open PowerShell as an administrator and run:

    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
    ```

2.  **Install PowerShellGet**: If you are using an older version of PowerShell, you may need to update PowerShellGet:

    ```powershell
    Install-Module -Name PowerShellGet -Force
    ```

3.  **Install the MS Graph Module**: Install the main module from the PowerShell Gallery.

    ```powershell
    Install-Module Microsoft.Graph -Scope CurrentUser
    ```

    To install for all users, run PowerShell as an administrator and use `-Scope AllUsers`.

### 2.2. Authentication

Microsoft Graph PowerShell supports two authentication methods:

*   **Delegated Access**: The script runs with the permissions of the signed-in user. This is suitable for interactive sessions.
*   **App-Only Access**: The script authenticates as an application using a client ID and a secret or certificate. This is ideal for automation and unattended scripts.

#### 2.2.1. Connecting with Delegated Permissions

To connect with delegated permissions, you specify the required permission scopes. You will be prompted to sign in interactively.

```powershell
# Example: Connect with permissions to read users and manage groups
Connect-MgGraph -Scopes "User.Read.All", "Group.ReadWrite.All"
```

#### 2.2.2. Connecting with App-Only Permissions

For automation, you will use app-only permissions with an Azure AD application registration.

**Using a Client Secret:**

```powershell
$clientId = "YOUR_APP_CLIENT_ID"
$tenantId = "YOUR_TENANT_ID"
$clientSecret = "YOUR_CLIENT_SECRET"

$securePassword = ConvertTo-SecureString -String $clientSecret -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($clientId, $securePassword)

Connect-MgGraph -TenantId $tenantId -ClientSecretCredential $credential
```

**Using a Certificate:**

```powershell
$clientId = "YOUR_APP_CLIENT_ID"
$tenantId = "YOUR_TENANT_ID"
$thumbprint = "YOUR_CERTIFICATE_THUMBPRINT"

Connect-MgGraph -ClientId $clientId -TenantId $tenantId -CertificateThumbprint $thumbprint
```

## 3. Using Azure Cloud Shell

Azure Cloud Shell is a browser-based shell for managing Azure resources. It comes pre-configured with many tools, including the Azure CLI and PowerShell.

### 3.1. Accessing Cloud Shell

You can access Cloud Shell in a few ways:

*   Directly at [shell.azure.com](https://shell.azure.com)
*   From the Azure portal by clicking the Cloud Shell icon in the top navigation bar.

### 3.2. Using MS Graph in Cloud Shell

The Microsoft Graph PowerShell module may not be installed by default in Cloud Shell. You can install it for your user profile:

```powershell
Install-Module Microsoft.Graph -Scope CurrentUser
```

Once installed, you can use the `Connect-MgGraph` cmdlets as described in the previous section. Your Azure login context in Cloud Shell can be used to seamlessly authenticate for delegated permissions.

## 4. Next Steps

With the Microsoft Graph PowerShell SDK installed and configured, you can now start managing your Azure AD and Microsoft 365 resources. Refer to the official [Microsoft Graph PowerShell documentation](https://learn.microsoft.com/en-us/powershell/microsoftgraph/get-started?view=graph-powershell-1.0) for a complete list of cmdlets and usage examples.

The next step in our plan is to design the full-permission application registration. This will be covered in a separate document.
