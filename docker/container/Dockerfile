FROM conda/miniconda3

COPY ./requirements.txt  /setup/
	
RUN apt-get update && apt-get install gcc -y && pip install --upgrade -r /setup/requirements.txt && \ 
    conda install -c r r-essentials

CMD ["python"]