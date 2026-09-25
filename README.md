# Solver-Level Warmstarting for Neural Network Verification

This repository contains the code, benchmark instances, experimental results, and analysis scripts used for the experiments in **[paper title]**.

The experiments combine tools from neural network verification and mixed-integer linear programming. In particular, we use modified versions of **VERONA**, **Marabou**, and **SYMPHONY**.

## Repository structure

```text
.
├── networks/          Neural networks used in the experiments
├── vnnlib/            Verification properties
├── scripts/
│   └── reformulate_mps.py
├── analysis/          Scripts used to analyse the experimental results
└── results/           Processed experimental results
```

The experiment configurations and experiment launcher are contained in our modified VERONA repository.

## Experimental pipeline

The experimental pipeline consists of the following steps:

```text
Networks + verification properties
                |
                v
             VERONA
       experiment management
                |
                v
             Marabou
        MILP formulation
                |
                v
             MPS file
                |
                v
      MPS reformulation
                |
                v
            SYMPHONY
       baseline / warmstart
                |
                v
             results
                |
                v
             analysis
```

VERONA is used to manage the experiments and interface with the verification and optimisation tools.

Marabou converts the neural network verification problems into MILP formulations. We modified Marabou to allow the generated Gurobi formulation to be exported as an MPS file.

The exported MPS formulations contain indicator constraints that are not directly supported by the version of SYMPHONY used in our experiments. `scripts/reformulate_mps.py` therefore reformulates these constraints before the MPS files are passed to SYMPHONY.

Finally, SYMPHONY is used to perform both the baseline and warmstarted optimisation experiments.

## Modified dependencies

The experiments rely on three modified external repositories.

### VERONA

Repository:

https://github.com/AWbosman/VERONA_symphony

VERONA is the experiment manager used throughout this work. Our fork adds a `VerificationModule` that interfaces with Marabou and SYMPHONY.

The configurations used for the experiments in the paper can be found under:

```text
scripts/OXFORD/
```

in the VERONA repository.

For reproducibility, the experiments should be run using our fork rather than the upstream VERONA package.

### Marabou

Repository:

https://github.com/AWbosman/Marabou

We use Marabou to generate MILP encodings of the neural network verification problems.

Our fork introduces a command-line option that exports the Gurobi-generated MILP formulation in MPS format and terminates after the formulation has been written.

Marabou must be built with Gurobi support enabled.

Please see the Marabou repository for its build requirements and Gurobi installation instructions.

### SYMPHONY

Repository:

https://github.com/AWbosman/SYMPHONY

SYMPHONY is used as the MILP solver for both the baseline and warmstarting experiments.

Our fork contains the code used to perform the warmstarting experiments reported in the paper. The experiments use the default SYMPHONY solver configuration unless otherwise stated.

## Installation

### 1. Clone this repository

```bash
git clone https://github.com/ADA-research/STAI-Solver-Level-Warmstarting-paper
cd https://github.com/ADA-research/STAI-Solver-Level-Warmstarting-paper
```

### 2. Clone and install VERONA

Clone the modified VERONA repository:

```bash
git clone https://github.com/AWbosman/VERONA_symphony.git
cd VERONA_symphony
```

We recommend creating a dedicated Python environment:

```bash
conda create -n verona_env python=3.10
conda activate verona_env
```

Install VERONA locally:

```bash
pip install -e .
```

### 3. Build Marabou

Clone our modified Marabou repository:

```bash
git clone https://github.com/AWbosman/Marabou.git
cd Marabou
mkdir build
cd build
```

Marabou needs to be compiled with Gurobi support:

```bash
cmake .. -DENABLE_GUROBI=ON
cmake --build .
```

A working Gurobi installation and licence are therefore required.

After compilation, the Marabou executable can be found under:

```text
Marabou/build/Marabou
```

### 4. Build SYMPHONY

Clone the modified SYMPHONY repository:

```bash
git clone https://github.com/AWbosman/SYMPHONY.git
```

Build SYMPHONY following the installation instructions provided in that repository.

**TODO:** Add the exact commands and dependency versions used to build SYMPHONY for the paper.

## Running the experiments

The experiments are launched through VERONA.

The configurations used for this paper are located in:

```text
VERONA_symphony/scripts/OXFORD/
```

These configurations specify the networks, verification instances, epsilon values, and solver setup used in the experiments.

Before running an experiment, update any machine-specific paths in the configuration to point to:

1. the networks in this repository;
2. the VNNLIB properties in this repository;
3. the compiled Marabou executable;
4. the compiled SYMPHONY executable; and
5. the desired output directory.

**TODO:** Document the exact configuration file(s) corresponding to each experiment in the paper.

An experiment can then be launched from the VERONA environment using the corresponding script, for example:

```bash
python scripts/OXFORD/<experiment-script>.py
```

For large-scale experiments, the configurations can be run through the SLURM functionality provided by VERONA.

## MPS reformulation

Marabou first generates an MPS representation of the verification problem.

Before passing this formulation to SYMPHONY, run:

```bash
python scripts/reformulate_mps.py input.mps output.mps
```

The script replaces the relevant indicator constraints with an equivalent formulation that can be processed by SYMPHONY.

**TODO:** Clarify whether this step is called automatically by the `VerificationModule` or needs to be executed separately.

## Reproducing the analysis

Processed experimental results are provided in:

```text
results/
```

This makes it possible to reproduce the analysis without rerunning all verification and optimisation experiments.

To regenerate the tables and figures:

```bash
python analysis/analyse_results.py
```

The analysis reads the combined experimental results and generates the summary statistics and figures used in the paper.

## Reproducibility levels

The repository supports three levels of reproduction.

**Analysis only.** Use the processed results in `results/` and run the analysis scripts. This does not require VERONA, Marabou, Gurobi, or SYMPHONY.

**Solver experiments.** Use the generated MPS instances and rerun the baseline and warmstarting experiments with SYMPHONY.

**Full experimental pipeline.** Starting from the neural networks and verification properties, use VERONA and Marabou to generate the MILP instances, reformulate them, solve them using SYMPHONY, and reproduce the subsequent analysis.

## Data

The neural networks and verification properties used in the experiments are included in this repository.

Processed results required to reproduce the analysis are provided under `results/`.

The complete raw experimental results and generated MPS formulations are available at:



## Citation

If you use this code or data, please cite:

```bibtex
@article{BosmanEtAl6,  
    author = {Bosman, Annelot W. and Liu, Minghao and Kwiatkowska, Marta and Hoos, Holger H. and van Rijn, Jan N.},
    title = {Exploring Solver-Level Warmstarting
for Neural Network Verification},
    year = {2026},
    journal = {WORKSHOP ON SECURE AND TRUSTWORTHY AI co-located with European Conference on Machine Learning and Principles and Practice of Knowledge Discovery in Databases},

}
```

## Licences and external software

This repository contains code developed for the experiments described in the paper. VERONA, Marabou, SYMPHONY, Gurobi, and the benchmark networks are distributed under their respective licences.

Please consult the individual repositories and data sources for their licensing terms.