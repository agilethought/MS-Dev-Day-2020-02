az acr login --name myregistry
cd <dockerfile directory
docker build -t <image_name> . 
docker tag <image_name> <myregistry.azurecr.io/<image_name>>
docker push <myregistry.azurecr.io/<image_name>>