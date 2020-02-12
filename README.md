# AgileThought MS Dev Day Workshop

## Context

Today, we'll be discussing and developing an Azure DevOps pipeline wrapped around an Azure MLOps pipeline to proactively scale a Kubernetes cluster based on Machine Learning predictions.

At the end of the workshop, your Azure account will contain a working instance of this configuration for reference and experimentation.

We have included three Azure DevOps "challenges" over the course the workshop.  We will update this documentation with solutions to these challenges as we go.

## Steps

### Azure Account Setup

> NOTE: This workshop is going to involve provisioning and configuring Azure resources such as ML Pipelines, Kubernetes Clusters, Azure Active Directory App Registrations, and Azure DevOps projects.  If you already have a corporate Azure account, there's a good chance that you do not have permission to take these actions.  If that's the case, we recommend that you sign up for a fresh Azure Free Account.

1. Create a new Azure Free Account *(if necessary)*
    - Navigate to https://azure.microsoft.com/en-us/free/
    - Select the "Start free" button

### Pick a Unique Identifier

We are going to need to create Azure resources that need globally unique identifiers.  To do this, we're going to use a "base name prefix" throughout the workshop. **This prefix should be 7-8 characters and only contain numbers and lowercase letters.**  Pick an identifier of the following format and write it down:

```
<your-initials><4 random digits>
```

For instance, I might pick `mms4721`.  You will use this wherever you see the `<baseName>` token in scripts and variables.

### Kubernetes Cluster Provisioning

Provisioning the Kubernetes cluster can take a few minutes.  Let's crack open Azure Cloud Shell and get that started in the background.

1. Navigate to the Azure Cloud Shell at https://shell.azure.com
1. Use the following script to create an Azure Resource Group, Service Principal, and AKS Cluster ([docs](https://docs.microsoft.com/en-us/azure/aks/kubernetes-walkthrough))
    ```
    # az login # Not required in Azure Cloud Shell

    # If you've already run this script, you'll need to remove cached service principal info in Azure
    # rm .azure/aksServicePrincipal.json

    az group create --name <baseName>-AML-RG --location eastus

    az provider register --namespace Microsoft.Network
    az provider register --namespace Microsoft.Compute
    az provider register --namespace Microsoft.Storage

    az ad sp create-for-rbac --name atmsdevdayapp

    # `aks create` will take a while!
    # substitute values from `create-for-rbac` above!
    az aks create --resource-group <baseName>-AML-RG \
        --name atDevDayCluster \
        --service-principal <appId from create-for-rbac> \
        --client-secret <password from create-for-rbac> \
        --node-count 1 \
        --vm-set-type VirtualMachineScaleSets \
        --enable-cluster-autoscaler \
        --generate-ssh-keys \
        --node-vm-size Standard_D2_v3 \
        --min-count 1 \
        --max-count 2

    # disable auto-scaling so we can proactively scale!
    az aks update --resource-group <baseName>-AML-RG --name atDevDayCluster --disable-cluster-autoscaler
    ```  
    ![Azure Cloud Shell AKS Creation](./readme_images/azure_cloud_shell_aks.png)
    - If you get Service Principal errors, review the following article: [Service principals with Azure Kubernetes Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/kubernetes-service-principal)
    - This script will take a few minutes to provision the cluster

### Back to the Presentation - Explaining the Problem Context