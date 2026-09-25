import os
import subprocess
import shutil
import sys
from pathlib import Path
import time
import argparse
import re
from typing import List, Tuple, Optional
import json
import csv
# from WARMSTART_PROJECT.pipeline.mps_reformulate import reformulate


SYMPHONY_TIMEOUT =3600

_re_user_time = re.compile(
    r"^\s*Total User Time\s+([0-9]*\.?[0-9]+)\s*$",
    re.MULTILINE
)
_re_presolve_time = re.compile(
    r"Total Presolve Time:\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE
)
_re_found = re.compile(r"Solution Found:\s*Node\s+(\d+),\s*Level\s+(\d+)")
_re_infeas = re.compile(r"infeasib", re.IGNORECASE)
_re_timelimit = re.compile(r"Time Limit Reached", re.IGNORECASE)
_re_presolve = re.compile(r"Total Presolve Time:\s+[0-9]*\.?[0-9]+")

def parse_symphony_log(text: str) -> Tuple[
    List[float],
    List[bool],
    List[bool],
    List[bool],
]:
    times: List[float] = []
    solution_found: List[bool] = []
    infeasible: List[bool] = []
    time_limit: List[bool] = []

    starts = [m.start() for m in _re_presolve.finditer(text)]
    if not starts:
        return times, solution_found, infeasible, time_limit

    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunk = text[s:e]

        infeasible.append(bool(_re_infeas.search(chunk)))
        time_limit.append(bool(_re_timelimit.search(chunk)))
        solution_found.append(bool(_re_found.search(chunk)))

        # Prefer Total User Time, fall back to Total Presolve Time
        m_user = _re_user_time.search(chunk)
        if m_user:
            times.append(float(m_user.group(1)))
        else:
            m_pre = _re_presolve_time.search(chunk)
            if m_pre:
                times.append(float(m_pre.group(1)))
            else:
                # Extremely defensive fallback
                times.append(0.0)

    return times, solution_found, infeasible, time_limit
        

    
def run_symphony_script(symphony_script, mps_path_origin, mps_path_target):
    symphony_cmd = [str(symphony_script),
                    "-F",
                    str(mps_path_origin),
                    "-F",
                    str(mps_path_target)
    ]
    
    try:
        env = os.environ.copy()
        result = subprocess.run(symphony_cmd,
          capture_output=True,
            text=True,
            env=env,
            timeout=SYMPHONY_TIMEOUT,
            cwd=str(symphony_script.parent))
        
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode
    except subprocess.TimeoutExpired as e:
        print("SYMPHONY timed out")
        sys.exit(2)
    except Exception as e:
        print("Exception running SYMPHONY: ", e)
        sys.exit(3)
        
    with open("symphony.log", "w") as f:
        f.write(stdout)
        
    return parse_symphony_log(stdout)
    
    
CSV_HEADER = ['first_mps', 'second_mps', 'result', 'time', 'warmstart_type', 'configuration']
   
def append_result(csv_path: Path, first_mps, second_mps, result, time, warmstart_type, configuration):
    write_header = not csv_path.exists()
    with open(csv_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if write_header:
            writer.writeheader()
        writer.writerow({
            'first_mps': first_mps,
            'second_mps': second_mps,
            'result': result,
            'time': time,
            'warmstart_type' :warmstart_type,
            'configuration': configuration, 
        })

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symphony_script', type=Path, default=None)
    parser.add_argument('--mps_path_first', type=Path, default=None)
    parser.add_argument('--mps_path_second', type= Path, default = None)
    parser.add_argument('--result_csv', type=Path)
    parser.add_argument('--warmstart_type', type=str)
    parser.add_argument('--configuration', type=str)
    args = parser.parse_args()

    model1 = args.mps_path_first
    model2 = args.mps_path_second
    symphony_script = args.symphony_script
    result_csv = args.result_csv
  
    user_times, solution_found, infeasible,time_limit = run_symphony_script(symphony_script, model1, model2)


    if solution_found and solution_found[-1]:
        result = "SAT"
    elif infeasible and infeasible[-1]:
        result = "UNSAT"
    elif time_limit and time_limit[-1]:
        result = "TIMEOUT"
    else:
        result = "ERR"

    total_time = user_times[-1] if user_times else None
    

    append_result(result_csv, model1, model2, result, total_time, args.warmstart_type, args.configuration)
    
    