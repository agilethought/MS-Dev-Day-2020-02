docker run -v $(System.DefaultWorkingDirectory)/_model-build/mlops-pipelines/python_scripts/:/script \
 -w=/script -e SP_APP_ID=$SP_APP_ID -e SP_APP_SECRET=$SP_APP_SECRET -e TENANT_ID=$TENANT_ID \
 -e AKS_RG=$AKS_RG -e STORAGE_ACCT_NAME=$STORAGE_ACCT_NAME -e STORAGE_ACCT_KEY=$STORAGE_ACCT_KEY \
 -e STORAGE_BLOB_NAME=$STORAGE_BLOB_NAME -e CONTANER_NAME=$CONTANER_NAME -e AKS_NAME=$AKS_NAME \
markschabacker/at_ml_dev_day:latest python AksResourceController.py
