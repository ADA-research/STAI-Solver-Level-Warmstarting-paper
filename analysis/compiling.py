import pandas as pd 
import os 
import argparse
import csv
import subprocess
import time
from pathlib import Path
from typing import List
import itertools
import json
import stat
from decimal import Decimal,getcontext

class OneInstance:
    def __init__(self, row):
        self.epsilon_value = float(row['epsilon_value'])
        self.result = row.get('result', None)
        self.time = row.get('time', None)
        self.verifier = row.get('verifier', None)
        self.network_name = row.get('network_name', None)
        self.image_name = row.get('image_name', None)
        self.mps_path = row.get('mps_path', None)
    def __repr__(self):
        return (f"OneInstance(net={self.network_name}, img={self.image_name}, "
                f"eps={self.epsilon_value}, res={self.result})")

class TwoInstance:
    def __init__(self, first_instance: OneInstance, second_instance: OneInstance, warmstart_type:str):
        self.first = first_instance
        self.second = second_instance
        # placeholders for outputs after running the warmstart experiment
        self.second_result = None
        self.second_time = None
        self.warmstart_type = warmstart_type
    def __repr__(self):
        return f"TwoInstance({self.first} -> {self.second})"
    
    
base_path = '/home/annelot/WARMSTART_PROJECT/baseline_symphony_21-01-2026+15_00/tmp'

df_list = []


for network_name in os.listdir(base_path):
    network_path = os.path.join(base_path, network_name)
    

    if os.path.isdir(network_path):
        for image_name in os.listdir(network_path):
            split_path = os.path.join(network_path, image_name)
   
            csv_path = os.path.join(split_path, "epsilons_df.csv")
            
            if os.path.exists(csv_path):
                # Read the distribution CSV
                df = pd.read_csv(csv_path)
                df['network_name'] = network_name
                df['image_name'] = image_name
                getcontext().prec = 20  # avoid precision loss

                df['epsilon_value'] = df['epsilon_value'].apply(
                    lambda x: float(Decimal(str(x)).quantize(Decimal('0.001'))))
                
                df['mps_path']  = split_path+ "/"+ network_name+ "_"+ image_name.removeprefix("image_")+ "_"+ df["epsilon_value"].astype(str).str.replace(".", "_", regex=False)+ ".mps"
                df_list.append(df)
                
combined_df = pd.concat(df_list, ignore_index=True)
combined_df.to_csv("baseline_results_per_epsilon.csv", index=False)

combined_df = pd.read_csv("baseline_results_per_epsilon.csv")
df = combined_df



df = df[df['result'] != 'ERR']
# df = df.drop_duplicates()

#Create an instance for each of the results. 
instances = {}
for _, row in df.iterrows():
    one = OneInstance(row)
    net = one.network_name
    img = one.image_name
    eps = one.epsilon_value
    instances.setdefault(net, {}).setdefault(img, {})[eps] = one


def sorted_eps_list(mapping_eps_to_oneinstance):
    # returns sorted list of eps values (ascending)
    return sorted(mapping_eps_to_oneinstance.keys())

def safe_get_instance(mapping, net, img, eps):
    try:
        return mapping[net][img][eps]
    except KeyError:
        return None
    
new_experiments = []

warmstart_types = ["UNSAT-UNSAT", "SAT-SAT", "SAT-TIMEOUT", "UNSAT-TIMEOUT", "IMAGE","NETWORK" ]
for net, images_dict in instances.items():
    for img, eps_map in images_dict.items():

        # slice the df for this (net,img) to extract results and ensure sort
        sliced = df[(df['network_name'] == net) & (df['image_name'] == img)].copy()
        sliced['epsilon_value'] = sliced['epsilon_value'].astype(float)
        sliced = sliced.sort_values('epsilon_value')

        # lists of eps by result label
        unsats = sliced[sliced['result'] == 'UNSAT']['epsilon_value'].tolist()
        sats = sliced[sliced['result'] == 'SAT']['epsilon_value'].tolist()
        timeouts_or_missing = sliced[sliced['result'].isnull() | (sliced['result']=='TIMEOUT')]['epsilon_value'].tolist()
        
        unsats_sorted = sorted(unsats)
        sats_sorted   = sorted(sats)

        if len(unsats_sorted) > 1:
            for i, eps_a in enumerate(unsats_sorted[:-1]):
                for eps_b in unsats_sorted[i+1:]:
                    inst_a = instances[net][img][eps_a]   # source (smaller eps)
                    inst_b = instances[net][img][eps_b]   # target (larger eps)
                    if inst_a is not inst_b:
                        new_experiments.append(TwoInstance(inst_a, inst_b, "UNSAT-UNSAT"))

        if len(sats_sorted) > 1:
            for i, eps_target in enumerate(sats_sorted[:-1]):
                for eps_source in sats_sorted[i+1:]:
                    inst_source = instances[net][img][eps_source]  # larger eps
                    inst_target = instances[net][img][eps_target]  # smaller eps
                    if inst_source is not inst_target:
                        new_experiments.append(
                            TwoInstance(inst_source, inst_target, "SAT-SAT")
                        )


        eps_sorted = sorted_eps_list(instances[net][img])
        for missing_eps in timeouts_or_missing:
            candidates = [e for e in eps_sorted if e not in timeouts_or_missing]
            if not candidates:
                continue
        
            nearest = min(candidates, key=lambda x: abs(x - missing_eps))
            solved_inst = safe_get_instance(instances, net, img, nearest)
            missing_inst = safe_get_instance(instances, net, img, float(missing_eps))
            if solved_inst and missing_inst:
                if solved_inst.result == "SAT":
                    new_experiments.append(TwoInstance(solved_inst, missing_inst, "SAT-TIMEOUT"))
                else:
                    new_experiments.append(TwoInstance(solved_inst, missing_inst, "UNSAT-TIMEOUT"))
                        

    
        for eps in eps_sorted:
            other_imgs = [other_img for other_img in instances[net] if other_img != img and eps in instances[net][other_img]]
            if other_imgs:
                other_inst = instances[net][other_imgs[0]][eps]
                this_inst = eps_map[eps]
                new_experiments.append(TwoInstance(this_inst, other_inst, "IMAGE"))


    image_index = {}
    for net, images_dict in instances.items():
        for img, eps_map in images_dict.items():
            for eps, one in eps_map.items():
                image_index.setdefault(img, {}).setdefault(eps, []).append((net, one))

    for img, eps_map in image_index.items():
        for eps, net_list in eps_map.items():
            if len(net_list) >= 2:
                # pair first two networks for an experiment
                inst_a = net_list[0][1]
                inst_b = net_list[1][1]
                new_experiments.append(TwoInstance(inst_a, inst_b, "NETWORK"))

seen = set()
unique_experiments = []
for t in new_experiments:
    sig = (t.first.network_name, t.first.image_name, t.first.epsilon_value,
           t.second.network_name, t.second.image_name, t.second.epsilon_value)
    if sig not in seen:
        seen.add(sig)
        unique_experiments.append(t)

print("the number of unique experiments is:", len(unique_experiments))


def run_job(symphony_code, instance:TwoInstance, result_csv):
    configuration = "None"
    
    slurm_script_template = (
    "#!/bin/sh\n"
    "#SBATCH --job-name=retry\n"
    "#SBATCH --partition=lovelace\n"
    "#SBATCH --output={slurm_scripts_path}/slurm_output_%A_%a.out\n"
    "python /home/annelot/WARMSTART_PROJECT/analysis/main.py"
    " --symphony_script {script_path}"
    " --mps_path_first {model1} "
    " --mps_path_second {model2} "
    " --warmstart_type {warmstart_type} "
    " --result_csv {result_csv} "
    " --configuration {configuration} \n"
    )
    slurm_script_path ="/home/annelot/WARMSTART_PROJECT/slurm"
    slurm_script_content = slurm_script_template.format(
        slurm_scripts_path=slurm_script_path,
        script_path=symphony_code,
        model1=instance.first.mps_path,
        model2=instance.second.mps_path,
        warmstart_type = instance.warmstart_type,
        result_csv=result_csv,
        configuration = configuration,
    )
    temp_slurm_script = Path(f"{slurm_script_path}/slurmscript_{os.path.basename(instance.first.mps_path)}_{os.path.basename(instance.second.mps_path)}.sh")
    with open(temp_slurm_script, "w") as f:
        f.write(slurm_script_content)
    os.chmod(temp_slurm_script, stat.S_IRWXU)
    os.system(f"sbatch {temp_slurm_script}")
        
        
    

for i, two in enumerate(unique_experiments, start=1):

    run_job("/home/annelot/coinbrew/SYMPHONY/SYMPHONY/Examples/warm_start_two_mps", two, "/home/annelot/WARMSTART_PROJECT/analysis/results_warmstart2.csv")
