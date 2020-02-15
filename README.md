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
1. Verify that AKS Cluster has been created correctly
    1. `Azure Portal -> Kubernetes services -> atDevDayCluster -> Settings -> Node pools`
        - `nodepool1` should be present and `Node count` should be `1`  
        ![AKS Cluster Node Pool](./readme_images/aks_cluster_node_pool.png)

Congratulations! You have created an AKS Cluster.  We will use the ML models to proactively scale the cluster later in the workshop.

### Azure and Azure DevOps Setup

1. Record Azure Service Principal Information and Create a Client Secret
    - `Portal -> Azure Active Directory -> App registrations -> atmsdevdayapp`
    - Record the following:
        - Application (client) ID
        - Directory (tenant) ID
    - Create a Client Secret
        - `Portal -> AAD -> App Registrations -> <This Registration> -> Certificates & secrets -> New client secret`
            - Description: `AT Dev Day Client Secret`
            - Expires: `Never`
        - Record Client Secret value  
        ![Client Secret Screen](./readme_images/client_secret.png)
1. Create a new Azure DevOps Organization *(if necessary)* ([docs](https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/create-organization?view=azure-devops))
    - Navigate to https://azure.microsoft.com/en-us/pricing/details/devops/azure-devops-services/
    - Select the Basic Plan column's "Start free >" button
1. Create a new Azure DevOps Project ([docs](https://docs.microsoft.com/en-us/azure/devops/organizations/projects/create-project?view=azure-devops&tabs=browser))
    - `Azure DevOps Organization Screen -> + New project (top right)`
1. Clone the source repo into your project
    - `Sidebar -> Repos -> Import -> https://github.com/agilethought/MS-Dev-Day-2020-02`  
    ![Import Repo](./readme_images/import_repo.png)
1. Capture Configuration Data in an Azure DevOps Variable Group
    - `Azure DevOps Project -> Sidebar -> Pipelines -> Library -> Variable Groups -> "+ Variable group`
        - Variable group name: `devopsforai-aml-vg`
        - Add the following variables:

            | Variable Name | Suggested Value |
            | ------------- | --------------- |
            | AML_COMPUTE_CLUSTER_NAME | `train-cluster` |
            | BASE_NAME | `<baseName>` |
            | EXPERIMENT_NAME | `mlopspython` |
            | LOCATION | `eastus` |
            | MODEL_NAME | `sklearn_regression_model.pkl` |
            | SOURCES_DIR_TRAIN | `python_scripts` |
            | SP_APP_ID | `<Application (client) ID from above>` |
            | SP_APP_SECRET | `<Client Secret Value from above>` |
            | SUBSCRIPTION_ID | `<Azure Subscription ID>` |
            | TENANT_ID | `<Directory (tenant) ID from above>` |
            | TRAIN_SCRIPT_PATH | `train.py` |
            | TRAINING_PIPELINE_NAME | `training-pipeline` |
1. Create an Azure Resource Manager Service Connection ([docs](https://docs.microsoft.com/en-us/azure/devops/pipelines/library/service-endpoints?view=azure-devops&tabs=yaml#create-a-service-connection))
    - `Azure DevOps Project Sidebar -> Project settings -> Pipelines -> Service connections -> + New service connection -> Azure Resource Manager -> Service principal (automatic)`
        - Subscription: `<Your Azure Subscription>`
        - Scope Level: `Subscription`
        - Resource Group: Leave Blank  
        - Service connection name: `AzureResourceConnection`
    ![Azure Resource Manager Service Connection](./readme_images/azure_resource_manager_service_connection.png)
1. Create a Build to Provision Azure Resources
    1. `Azure DevOps Project Sidebar -> Pipelines -> Create Pipeline`
        - Where is your code?: `Azure Repos Git`
        - Select your imported repo
        - Configure your pipeline: `Existing Azure Pipelines YAML file`
            - Branch: `master`
            - Path: `/build_pipeline_scripts/iac-create-environment.yml`
        - Suggested Name: `Provision Azure Environment`
    1. Run the Build
        - `Newly Created Build Pipeline -> Run` (This will take a few minutes!)
    1. Verify Azure Resource Creation
        - `Azure Portal -> Resource groups -> <baseName>-AML-RG`
        - Verify that 5 resources have been created:  
        ![Initial Resource Group Members](./readme_images/initial_resource_group_members.png)

Congratulations!  You have configured the large majority of the Azure resources necessary for this workshop.

## Create the ML Pipeline

1. Create a Blob Container and Load Log Data
    1. `Azure Portal -> Storage Accounts -> <baseName>amlsa -> Blob Service -> Containers > + Container`
        - Name: `modeldata`
        - Public access level: `Private (no anonymous access)`
    1. Select the newly created `modeldata` container
        - Download [`log_data.pkl`](https://github.com/agilethought/MS-Dev-Day-2020-02/raw/master/data/log_data.pkl)
        - Upload (top left)
            - File: `log_data.pkl` that you just downloaded
1. Capture Blob Storage Variable Group Entries
    - `Azure DevOps Project -> Sidebar -> Pipelines -> Library -> Variable Groups -> devopsforai-aml-vg`
        - Add the following variables:

            | Variable Name | Suggested Value |
            | ------------- | --------------- |
            | STORAGE_ACCT_NAME | `<baseName>amlsa` |
            | STORAGE_ACCT_KEY | `<Azure Portal -> Storage Accounts -> <Your Storage Account> -> Settings -> Access Keys>` |
            | STORAGE_BLOB_NAME | `modeldata` |
1. Create an Azure DevOps Pipeline to Create the ML Pipeline
    1. `Azure DevOps Project Sidebar -> Pipelines -> Pipelines -> New pipeline`
        - Where is your code?: `Azure Repos Git`
        - Select your imported repo
        - Configure your pipeline: `Existing Azure Pipelines YAML file`
            - Branch: `master`
            - Path: `/build_pipeline_scripts/model-build.yml`
        - Suggested Name: `Build ML Pipeline`
    1. Run the Pipeline
        - `Newly Created Build Pipeline -> Run` (This will take a few minutes!)
        - Verify that ML Pipeline was created
            - `Azure Portal -> Machine Learning -> <Your ML Workspace> -> Pipelines`
            - You should see a pipeline named `training-pipeline`  
            ![ML Pipeline Created](./readme_images/ml_pipeline_created.png)

Congratulations!  You have created an Azure ML Pipeline.  We will train the pipeline in the next section.

## Train the ML Pipeline
1. Create a New Azure DevOps Release
    1. `Azure DevOps Project Sidebar -> Pipelines -> Releases -> New pipeline`
        - Start With: `Empty Job`
            - Stage Name: `Run Train Scripts`
    1. Update name to `Train ML Pipeline`
    1. Add an Artifact
        - Source Type: `Build`
        - Source: `Build ML Pipeline` (the pipeline created from `model-build.yml`)
        - Default version: `Latest`
        - Source Alias: `_model-build`  
        ![Add Artifact](./readme_images/add_artifact.png)
    1. Link the Variable Group
        - `Train ML Pipeline Release -> Variables Tab -> Variable groups`
        - Link Variable Group: `devopsforai-aml-vg`
    1. Update to Ubuntu Agent
        1. Navigate into Tasks for the Release
        2. Select the "Agent Job"
        3. Update Agent Specification: `ubuntu-16.04`
    1. Add Command Line Task
        1. Click the "+" (Add task to an Agent Job) button in the `Agent Job` item
        1. Add a `Command line` task
        1. Select the new `Command Line Script` task and set the following
            - Display Name: `Run Train Models Script`
            - Script:
            ```
            docker run -v $(System.DefaultWorkingDirectory)/_model-build/mlops-pipelines/python_scripts/:/script \
            -w=/script -e MODEL_NAME=$MODEL_NAME -e EXPERIMENT_NAME=$EXPERIMENT_NAME \
            -e TENANT_ID=$TENANT_ID -e SP_APP_ID=$SP_APP_ID -e SP_APP_SECRET=$SP_APP_SECRET \
            -e SUBSCRIPTION_ID=$SUBSCRIPTION_ID -e RELEASE_RELEASEID=$RELEASE_RELEASEID \
            -e BUILD_BUILDID=$BUILD_BUILDID -e BASE_NAME=$BASE_NAME \
            -e STORAGE_ACCT_NAME=$STORAGE_ACCT_NAME -e STORAGE_ACCT_KEY=$STORAGE_ACCT_KEY -e STORAGE_BLOB_NAME=$STORAGE_BLOB_NAME \
            mcr.microsoft.com/mlops/python:latest python run_train_pipeline.py
            ```  
            ![Run Train Models](./readme_images/run_train_models_script.png)
    1. Run the Release
        - Verify that models are created (this may take a while!)
            - `Azure Portal -> Machine Learning -> <baseName>-AML-WS -> Pipelines -> training-pipeline -> Summary -> Last Run Result: Finished`
            ![Pipeline Finished](./readme_images/pipeline_status_finished.png)
            - `Azure Portal -> Machine Learning -> <baseName>-AML-WS -> Models`  
            ![Trained Models](./readme_images/trained_models.png)
        - Verify that models exist in blob storage
            - `Azure Portal -> Storage Accounts -> <baseName>amlsa -> Blob Service -> Containers -> modeldata`  
            ![Trained Model Blobs](./readme_images/trained_models_pkls.png)

Congratulations!  You've trained your models.  We will scale the AKS cluster from the start of the workshop in the next section.

## Proactively Scale the AKS Cluster using Azure ML

1. Capture AKS Variable Group Entries
    - `Azure DevOps Project -> Sidebar -> Pipelines -> Library -> Variable Groups -> devopsforai-aml-vg`
        - Add the following variables:

            | Variable Name | Suggested Value |
            | ------------- | --------------- |
            | AKS_NAME | `atDevDayCluster` |
            | AKS_RG | `<baseName>-AML-RG` |
1. Create a new Azure DevOps Release to run the ML Scaler
    1. `Azure DevOps Project Sidebar -> Pipelines -> Releases -> Train ML Pipeline -> ... in top right -> Clone`
        - Name: `Run ML Scaler`
        - Update the `Command Line Script` task to look like the following: 
            - Display Name: `Run ML Scaler Script`
            - Script:
            ```
            docker run -v $(System.DefaultWorkingDirectory)/_model-build/mlops-pipelines/python_scripts/:/script \
            -w=/script -e SP_APP_ID=$SP_APP_ID -e SP_APP_SECRET=$SP_APP_SECRET -e TENANT_ID=$TENANT_ID \
            -e AKS_RG=$AKS_RG -e STORAGE_ACCT_NAME=$STORAGE_ACCT_NAME -e STORAGE_ACCT_KEY=$STORAGE_ACCT_KEY \
            -e STORAGE_BLOB_NAME=$STORAGE_BLOB_NAME -e CONTANER_NAME=$CONTANER_NAME -e AKS_NAME=$AKS_NAME \
            markschabacker/at_ml_dev_day:latest python AksResourceController.py
            ```  
            ![Run ML Scaler](./readme_images/run_ml_scaler_script.png)
            - The docker image definition used in the script is available in the `docker/container` folder in this repo.
1. Save and run the `Run ML Scaler` release
    - This should take a while (5+ minutes)!
1. Verify Scaling
    - Review release logs  
        ![Release Log](./readme_images/scaler_release_logs.png)
    - Verify that AKS has been scaled
        - `Azure Portal -> Kubernetes services -> atDevDayCluster -> Settings -> Node pools -> nodepool1`
            - `Node count` should be `2`!  
            ![AKS Scaled](./readme_images/aks_scaled.png)

Congratulations!  You've used Machine Learning to proactively scale an Azure Kubernetes Service cluster!