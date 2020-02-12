from azureml.core.run import Run
from azure.cli.core import get_default_cli
import os
import argparse
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.externals import joblib
import numpy as np
from azure.storage.blob import BlockBlobService
import io

def make_time_series(x, length):
    xs = [x[idx:idx+length+1] for idx in range(len(x)-length)]
    x = [x[:length] for x in xs]
    y = [x[length] for x in xs]
    return np.array(x), np.array(y)

# parse args
parser = argparse.ArgumentParser("train")
parser.add_argument(
    "--release_id",
    type=str,
    help="The ID of the release triggering this pipeline run",
)
parser.add_argument(
    "--model_name",
    type=str,
    help="Name of the Model",
    default="sklearn_regression_model.pkl",
)
parser.add_argument(
    "--storageacctname",
    type=str,
    help="azure storage acct name"
)
parser.add_argument(
    "--storageacctkey",
    type=str,
    help="azure storage acct key"
)
parser.add_argument(
    "--containername",
    type=str,
    help="azure storage container name"
)
args = parser.parse_args()
import sklearn
print(sklearn.__version__)
print("Argument 1: %s" % args.release_id)
print("Argument 2: %s" % args.model_name)
print("Argument 3: %s" % args.storageacctname)
print("Argument 4: %s" % args.storageacctkey)
print("Argument 5: %s" % args.containername)
model_name = args.model_name
release_id = args.release_id

# prepare run context
run = Run.get_context()
exp = run.experiment
ws = run.experiment.workspace

# get data
block_blob_service = BlockBlobService(account_name=args.storageacctname, account_key=args.storageacctkey)
obj = block_blob_service.get_blob_to_bytes(args.containername, 'log_data.pkl')
a = io.BytesIO(obj.content)
x, y = joblib.load(a)

# train test split
split_at = int(x.shape[0] * 0.80)
x_train = x[:split_at]
x_test = x[split_at:]
y_train = y[:split_at]
y_test = y[split_at:]
print('DATA SHAPES', x_train.shape, y_train.shape, x_test.shape, y_test.shape)

# avg completion time
model = LinearRegression()
model.fit(x_train, y_train)
preds = model.predict(x_test)
run.log("avg_completion_time.pkl_r2", r2_score(preds, y_test))
joblib.dump(value=model, filename='avg_completion_time.pkl')
# register models
run.upload_file(name="./outputs/" + 'avg_completion_time.pkl', path_or_stream='avg_completion_time.pkl')
model_path = os.path.join('outputs', 'avg_completion_time.pkl')
run.register_model(
    model_name='avg_completion_time.pkl',
    model_path=model_path,
    properties={"release_id": release_id})
block_blob_service.create_blob_from_path(args.containername, 'avg_completion_time.pkl', 'avg_completion_time.pkl')

# user models
ts_models = ['admin_users.pkl', 'config_users.pkl', 'end_users.pkl']
lengths = [5, 7, 21]
for i, model_name in enumerate(ts_models):
    ts_x_train, ts_y_train = make_time_series([x[i] for x in x_train], lengths[i])
    ts_x_test, ts_y_test = make_time_series([x[i] for x in x_test], lengths[i])
    model = LinearRegression()
    model.fit(ts_x_train, ts_y_train)
    preds = model.predict(ts_x_test)
    run.log(model_name + "_r2", r2_score(preds, ts_y_test))
    joblib.dump(value=model, filename=model_name)
    # register models
    run.upload_file(name="./outputs/" + model_name, path_or_stream=model_name)
    model_path = os.path.join('outputs', model_name)
    run.register_model(
        model_name=model_name,
        model_path=model_path,
        properties={"release_id": release_id})
    block_blob_service.create_blob_from_path(args.containername, model_name, model_name)

# Add properties to identify this specific training run
run.add_properties({"release_id": release_id, "run_type": "train"})
print(f"added properties: {run.properties}")

run.complete()