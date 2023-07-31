if [[ $(basename '$0') = "env.sh" ]]; then
    echo "Please source this script: 'source env.sh'"
    exit 1  # not sourced
fi

if [[ ! -f _conda_env/bin/pip ]]; then
    conda create --prefix _conda_env python=3.10 -c conda-forge || exit 10
    conda activate $(realpath _conda_env)
    # conda install -c conda-forge ambertools
    # conda install -c conda-forge cxx-compiler==1.5.2 # gcc11
    # conda install -c conda-forge cudatoolkit cudatoolkit-dev
    if [[ -f requirements.txt ]]; then pip -v install -r requirements.txt; fi
fi

conda activate $(realpath _conda_env)
export LD_LIBRARY_PATH=$(realpath _conda_env/lib64):$LD_LIBRARY_PATH

# Use ssh tunnel on client
# ssh -4 -L 8501:127.0.0.1:8501 -N -f tyrion2.mse.gatech.edu
