from azureml.pipeline.core.graph import PipelineParameter
from azureml.pipeline.steps import PythonScriptStep
from azureml.pipeline.core import Pipeline  # , PipelineData
from azureml.core.runconfig import RunConfiguration, CondaDependencies
# from azureml.core import Datastore
import os
import sys
from dotenv import load_dotenv
from azureml.core import Workspace, Datastore
from azureml.core.authentication import ServicePrincipalAuthentication
from dotenv import load_dotenv
from azureml.core.compute import AmlCompute
from azureml.core.compute import ComputeTarget
from azureml.exceptions import ComputeTargetException
from azureml.data.data_reference import DataReference


def get_workspace(
        name: str,
        resource_group: str,
        subscription_id: str,
        tenant_id: str,
        app_id: str,
        app_secret: str):
    service_principal = ServicePrincipalAuthentication(
        tenant_id=tenant_id,
        service_principal_id=app_id,
        service_principal_password=app_secret)

    try:
        aml_workspace = Workspace.get(
            name=name,
            subscription_id=subscription_id,
            resource_group=resource_group,
            auth=service_principal)

        return aml_workspace
    except Exception as caught_exception:
        print("Error while retrieving Workspace...")
        print(str(caught_exception))
        sys.exit(1)

def get_compute(
    workspace: Workspace,
    compute_name: str,
    vm_size: str
):
    # Load the environment variables from .env in case this script
    # is called outside an existing process
    load_dotenv()
    # Verify that cluster does not exist already
    try:
        if compute_name in workspace.compute_targets:
            compute_target = workspace.compute_targets[compute_name]
            if compute_target and type(compute_target) is AmlCompute:
                print('Found existing compute target ' + compute_name
                      + ' so using it.')
        else:
            compute_config = AmlCompute.provisioning_configuration(
                vm_size=vm_size,
                vm_priority=os.environ.get("AML_CLUSTER_PRIORITY",
                                           'lowpriority'),
                min_nodes=int(os.environ.get("AML_CLUSTER_MIN_NODES", 0)),
                max_nodes=int(os.environ.get("AML_CLUSTER_MAX_NODES", 4)),
                idle_seconds_before_scaledown="300"
                #    #Uncomment the below lines for VNet support
                #    vnet_resourcegroup_name=vnet_resourcegroup_name,
                #    vnet_name=vnet_name,
                #    subnet_name=subnet_name
            )
            compute_target = ComputeTarget.create(workspace, compute_name,
                                                  compute_config)
            compute_target.wait_for_completion(
                show_output=True,
                min_node_count=None,
                timeout_in_minutes=10)
        return compute_target
    except ComputeTargetException as e:
        print(e)
        print('An error occurred trying to provision compute.')
        exit()

def main():
    load_dotenv()
    workspace_name = os.environ.get("BASE_NAME")+"-AML-WS"
    resource_group = os.environ.get("BASE_NAME")+"-AML-RG"
    subscription_id = os.environ.get("SUBSCRIPTION_ID")
    tenant_id = os.environ.get("TENANT_ID")
    app_id = os.environ.get("SP_APP_ID")
    app_secret = os.environ.get("SP_APP_SECRET")
    sources_directory_train = os.environ.get("SOURCES_DIR_TRAIN")
    train_script_path = os.environ.get("TRAIN_SCRIPT_PATH")
    vm_size = os.environ.get("AML_COMPUTE_CLUSTER_CPU_SKU")
    compute_name = os.environ.get("AML_COMPUTE_CLUSTER_NAME")
    model_name = os.environ.get("MODEL_NAME")
    build_id = os.environ.get("BUILD_BUILDID")
    pipeline_name = os.environ.get("TRAINING_PIPELINE_NAME")

    # Get Azure machine learning workspace
    aml_workspace = get_workspace(
        workspace_name,
        resource_group,
        subscription_id,
        tenant_id,
        app_id,
        app_secret)
    print(aml_workspace)

    # Get Azure machine learning cluster
    aml_compute = get_compute(
        aml_workspace,
        compute_name,
        vm_size)
    if aml_compute is not None:
        print(aml_compute)

    run_config = RunConfiguration(conda_dependencies=CondaDependencies.create(
        conda_packages=['numpy', 'pandas',
                        'scikit-learn', 'tensorflow', 'keras'],
        pip_packages=['azure', 'azureml-core',
                      'azure-storage',
                      'azure-storage-blob',
                      'azure-cli',
                      'azure-cli-telemetry',
                      'azure-cli-core',
                      'azure-cli-nspkg',
                      'azure-cli-command-modules-nspkg'])
    )
    run_config.environment.docker.enabled = True

    model_name = PipelineParameter(
        name="model_name", default_value=model_name)
    release_id = PipelineParameter(
        name="release_id", default_value="0"
    )
    storageacctname = PipelineParameter(
        name="storageacctname", default_value=os.environ.get("STORAGE_ACCT_NAME")
    )
    storageacctkey = PipelineParameter(
        name="storageacctkey", default_value=os.environ.get("STORAGE_ACCT_KEY")
    )
    containername = PipelineParameter(
        name="containername", default_value=os.environ.get("STORAGE_BLOB_NAME")
    )

    train_step = PythonScriptStep(
        name="Train Model",
        script_name=train_script_path,
        compute_target=aml_compute,
        source_directory=sources_directory_train,
        arguments=[
            "--release_id", release_id,
            "--model_name", model_name,
            "--storageacctname", storageacctname,
            "--storageacctkey", storageacctkey,
            "--containername", containername
        ],
        runconfig=run_config,
        allow_reuse=False,
    )
    print("Step Train created")

    steps = [train_step]

    train_pipeline = Pipeline(workspace=aml_workspace, steps=steps)
    train_pipeline.validate()
    published_pipeline = train_pipeline.publish(
        name=pipeline_name,
        description="Model training/retraining pipeline",
        version=build_id
    )
    print(f'Published pipeline: {published_pipeline.name}')
    print(f'for build {published_pipeline.version}')


if __name__ == '__main__':
    main()