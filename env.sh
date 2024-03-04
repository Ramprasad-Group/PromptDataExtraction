if [[ $(basename '$0') = "env.sh" ]]; then
    echo "Please source this script: 'source env.sh'"
    exit 1  # not sourced
fi

if [[ ! -f _conda_env/bin/pip ]]; then
    conda create --prefix _conda_env python=3.10 -c conda-forge || exit 10
    conda activate $(realpath _conda_env)

    conda install -c conda-forge cxx-compiler==1.5.2 # gcc11
    conda install -c conda-forge cudatoolkit cudatoolkit-dev
    conda install -c conda-forge postgresql=15

    pip -v install -r requirements.txt
    pip -v install -r pranav/requirements.txt

    cde data download

    python -m spacy download en_core_web_sm
fi

conda activate $(realpath _conda_env)
export LD_LIBRARY_PATH=$(realpath _conda_env/lib64):$LD_LIBRARY_PATH
export PYTHONPATH=.

# Use ssh tunnel on client to connect to the frontend
# ssh -4 -L 8501:127.0.0.1:8501 tyrion.mse.gatech.edu


update() {
    pip -v install -r requirements.txt
    python backend/sett/__init__.py
}

install_docs() {
    ## Install requirements to build docs.
    conda install -c conda-forge sphinx myst-parser

    ## Run the following to setup a new project.
    # sphinx-quickstart
}

docs() {
    ## Build docs as website for editing.
    ## Run from the vscode terminal in the ssh session.
    cd docs
    make html
    echo "Use vscode live preview to view docs/build/html/index.html"
}

docspdf() {
    ## Build docs in pdf format to share with others
    cd docs
    make latexpdf && \
        mv build/latex/rgthermosets.pdf ../User-Guide.pdf && \
        echo "Saved as User-Guide.pdf"
}

"$@"
