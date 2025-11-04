# Use a mambaforge image with conda pre-installed
FROM quay.io/condaforge/mambaforge:24.9.2-0

#base environemtn is Jupter server
#install JupyterLab and conda-lock in the base environment w/in base environ
#juypterlab runs here and discovers kernels from other environments
RUN mamba install -y -n base -c conda-forge jupyterlab conda-lock && mamba clean -tipy
#python environment is py-env
ARG PYTHON_ENV=py-env

#Copy the lock file
COPY conda-linux-64.lock conda-linux-64.lock

#Create dedicated py environ fromn lock file via mamba create
RUN mamba create -y -n $PYTHON_ENV --file conda-linux-64.lock && \
    mamba clean -tipy && \
    rm conda-linux-64.lock

# ensure ipykernel is present to register the environment.
RUN mamba install -y -n $PYTHON_ENV -c conda-forge ipykernel cartopy && \
    mamba clean -tipy
#installs pip dependencies into 'py-env'
#via conda run -n $PYTHON_ENV pip install...'
RUN conda run -n $PYTHON_ENV pip install --no-cache-dir https://github.com/cal-adapt/climakitae/archive/refs/tags/1.4.0.zip

#TODO later, get add'l python dependencies from requiremtnes.txt (now empty)
COPY requirements.txt /tmp/requirements.txt
RUN conda run -n $PYTHON_ENV pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

#register the Python kernel w/ Jupyter
RUN conda run -n $PYTHON_ENV python -m ipykernel install --user --name $PYTHON_ENV --display-name "Python (Climate)"

#~~R environment~~
# Define the environment name
ARG R_ENV=r-env

# dedicated R environment. This fixes hella problems with conflicing R dependecies by just isolating R istelf
RUN mamba create -y -n $R_ENV -c conda-forge r-base r-tidyverse r-irkernel && \
    mamba clean -tipy

#reg R kernel with Jupyter
RUN conda run -n $R_ENV Rscript -e "IRkernel::installspec(name = '${R_ENV}', displayname = 'R (Tidyverse)')"

# Keep container alive
CMD ["tail", "-f", "/dev/null"]