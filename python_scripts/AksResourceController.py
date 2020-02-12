from azure.cli.core import get_default_cli
from azure.storage.blob import BlockBlobService
from sklearn.externals import joblib
import os
import numpy as np
import io

class AksResourceController(object):
 
    def __init__(self, servicePrincipal, clientSecret, tenant, resourceGroup, 
                 storageAccountName, storageAccountKey, storageBlobName, clusterName, sla, threshold, 
                 scale_increment_nodes, min_nodes, model_endpoint):
        # initialize the object
        self.servicePrincipal = servicePrincipal
        self.clientSecret = clientSecret
        self.tenant = tenant
        self.resourceGroup = resourceGroup
        self.storageAccountName = storageAccountName
        self.storageAccountKey = storageAccountKey
        self.storageBlobName = storageBlobName
        self.clusterName = clusterName
        self.sla = sla
        self.threshold = threshold
        self.scale_increment_nodes = scale_increment_nodes
        self.min_nodes = min_nodes
        self.model_endpoint = model_endpoint
    
    def run(self):
        # run process
        print('======== AUTHENTICATE ========')
        self.authenticate()
        print('======== GET AKS STATE ========')
        self.get_current_nodes()
        print('======== LOAD DATA ========')
        self.load_data()
        print('======== LOAD MODELS ========')
        self.load_models()
        print('======== MAKE PREDICTION ========')
        self.make_prediction()
        print('======== CHANGE AKS STATE ========')
        self.verify_compliance()
        
    def authenticate(self):
        # authenticate to azure
        self.cli = get_default_cli()
        self.cli.invoke([
            'login',
            '--service-principal',
            '-u', self.servicePrincipal,
            '-p', self.clientSecret,
            '--tenant', self.tenant
        ])

    def get_current_nodes(self):
        # retrieve the current node count
        self.cli.invoke([
            'aks', 'show',
            '--resource-group', self.resourceGroup,
            '--name', self.clusterName
        ])
        self.current_nodes = self.cli.result.result['agentPoolProfiles'][0]['count'] # only handling 1st node pool
        
    def load_data(self):
        block_blob_service = BlockBlobService(account_name=self.storageAccountName, account_key=self.storageAccountKey)
        obj = block_blob_service.get_blob_to_bytes(self.storageBlobName, 'log_data.pkl')
        self.x, self.y = joblib.load(io.BytesIO(obj.content))
        
    def load_models(self):
        # load models
        models = [
            'avg_completion_time.pkl',
            'end_users.pkl',
            'config_users.pkl',
            'admin_users.pkl'
        ]
        for model in models:
            self.cli.invoke([
                'storage', 'blob', 'download',
                '--account-name', self.storageAccountName,
                '--container-name', self.storageBlobName,
                '--name', model,
                '--file', model
            ])
        self.avg_completion_time_model = joblib.load('avg_completion_time.pkl')
        self.end_user_model = joblib.load('end_users.pkl')
        self.config_user_model = joblib.load('config_users.pkl')
        self.admin_user_model = joblib.load('admin_users.pkl')
    
    def make_time_series(self, x, length):
        # utility to make a time series from a feature vector
        xs = [x[idx:idx+length+1] for idx in range(len(x)-length)]
        x = [x[:length] for x in xs]
        y = [x[length] for x in xs]
        return np.array(x), np.array(y)

    def make_prediction(self):
        # make predictions
        # TODO replace with hosted model endpoint calls
        end_users = self.end_user_model.predict(self.make_time_series([x[2] for x in self.x], 21)[0][-1].reshape((1,-1)))
        config_users = self.end_user_model.predict(self.make_time_series([x[1] for x in self.x], 21)[0][-1].reshape((1,-1)))
        admin_users = self.end_user_model.predict(self.make_time_series([x[0] for x in self.x], 21)[0][-1].reshape((1,-1)))
        instance = np.array([admin_users, config_users, end_users]).reshape((1,-1))
        self.prediction = self.avg_completion_time_model.predict(instance)[0]
    
    def scale(self, change):
        # change aks nodes
        print('SLA: ' + str(self.sla) + ', LOWER: ' + str(self.sla - self.threshold) + ', UPPER: ' + str(self.sla + self.threshold) + ', PRED: ' + str(self.prediction))
        print('CURR: ' + str(self.current_nodes) + ', CHG: ' + str(self.change))
        self.cli.invoke([
            'aks', 'scale',
            '--name', self.clusterName,
            '--node-count', str(change),
            '--resource-group', self.resourceGroup
        ])
                 
    def verify_compliance(self):
        # checks prediction versus SLA and triggers resource changes to meet SLA
        print(self.prediction, self.sla, self.threshold)
        if self.prediction > self.sla + self.threshold: # under-resourced
            self.change = max(self.current_nodes + self.scale_increment_nodes, self.min_nodes)
            self.scale(self.change) # at least one node running
        elif self.prediction < self.sla - self.threshold: # over-resourced
            self.change = self.current_nodes - self.scale_increment_nodes
            self.scale(self.change)
            
if __name__ == '__main__':
    aksrc = AksResourceController(
        servicePrincipal=os.environ.get("SP_APP_ID"),
        clientSecret=os.environ.get("SP_APP_SECRET"),
        tenant=os.environ.get("TENANT_ID"),
        resourceGroup=os.environ.get("AKS_RG"),
        storageAccountName=os.environ.get("STORAGE_ACCT_NAME"),
        storageAccountKey=os.environ.get("STORAGE_ACCT_KEY"),
        storageBlobName=os.environ.get("STORAGE_BLOB_NAME"),
        clusterName=os.environ.get("AKS_NAME"),
        sla=50, 
        threshold=20, 
        scale_increment_nodes=1, 
        min_nodes=2, 
        model_endpoint=None
    )
    aksrc.run()
    print('DONE')
