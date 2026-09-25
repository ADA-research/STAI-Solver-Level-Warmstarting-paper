#!/usr/bin/env python3
from decimal import Decimal, getcontext
import sys, re

getcontext().prec = 50

def toks(line):
    return line.strip().split()

# Find section start indices (zero-based index of the header line)
def update_categories(cats, s):
    for key in cats:
        cats[key] = None
        for i, l in enumerate(s):
            if l.strip().upper().startswith(key):
                cats[key] = i    # zero-based index of header line
                break
    return cats

def find_following(current, cats):
    """
    Return the key of the next section after 'current' (or None if none).
    Uses zero-based indices stored in cats.
    """
    smallest = None
    next_cat = None
    cur_start = cats[current]
    if cur_start is None:
        return None
    for cat, start in cats.items():
        if (cat != current) and (start is not None) and (start > cur_start):
            if smallest is None or start < smallest:
                smallest = start
                next_cat = cat
    return next_cat


def insert_column(variable,row, M, r_column, cats, s):
    from decimal import Decimal

    next_cat = find_following(r_column, cats)
    start_of_column_block = cats.get(r_column)
    if start_of_column_block is None:
        print("No MARKER section found - nothing to adjust.")
        return s

    start = start_of_column_block + 1
    end = cats[next_cat] if next_cat is not None else len(s)


    M = Decimal(str(M))
    changed = 0

    for i in range(start, end):
        line = s[i]
        if not line.strip():
            continue

        parts = toks(line)
        if len(parts) < 3:
            continue

        var_name = parts[0]   
        row_name = parts[1]   
        val_str  = parts[2] 

        if var_name == variable:
            try:
                val = Decimal(val_str)
            except Exception:
                # could be non-numeric (e.g., a parameter reference) — skip
                continue

            new_val = M
            leading_ws = re.match(r'^\s*', line).group(0)

            new_line = f"{leading_ws}{variable}     {row}       {str(new_val)}"
            s.insert(i, new_line)
            changed += 1
        
            print(f"Inserted column {i}: {var_name} {row_name} with upper {new_val}")
            return s

def adjust_rhs(row, M, r_rhs, cats, s):
    """
    Add 'bound' to all RHS entries for constraint named 'row' in RHS block.
    cats contains zero-based header indices (e.g., cats['RHS'] is index of 'RHS' header line).
    """
    from decimal import Decimal

    next_cat = find_following(r_rhs, cats)
    start_of_rhs_block = cats.get(r_rhs)

    # lines after the header until (but not including) next header (or EOF)
    start = start_of_rhs_block + 1
    end = cats[next_cat] if next_cat is not None else len(s)

    M= Decimal(str(M))
    changed = 0

    for i in range(start, end):
        line = s[i]
        if not line.strip():
            continue

        parts = toks(line)
        if len(parts) < 3:
            continue

        rhs_name = parts[0]   # e.g. RHS1
        row_name = parts[1]   # e.g. R99
        val_str  = parts[2]   # numeric RHS (may be scientific)

        if row_name == row:

            val = Decimal(val_str)
            new_val = val + M

            leading_ws = re.match(r'^\s*', line).group(0)


            new_line = f"{leading_ws}{rhs_name}      {row_name}       {str(new_val)}"
            s[i] = new_line
            changed += 1
            # debug print
            print(f"Adjusted RHS line {i}: {rhs_name} {row_name} : {val} -> {new_val}")

    if changed == 0:
        print(f"No RHS entries matched row='{row}' in RHS block (start={start}, end={end}).")
    return s

def adjust_rows(row, rows_cat, cats, s):
    from decimal import Decimal

    next_cat = find_following(rows_cat, cats)
    start_of_row_block = cats.get(rows_cat)

    # lines after the header until (but not including) next header (or EOF)
    start = start_of_row_block + 1
    end = cats[next_cat] if next_cat is not None else len(s)

    changed = 0

    for i in range(start, end):
        line = s[i]
        if not line.strip():
            continue

        parts = toks(line)
    

        if len(parts) < 2:
            continue
        
        row_name = parts[1] 

        if row_name == row:
            
            # preserve leading whitespace
            leading_ws = re.match(r'^\s*', line).group(0)
            new_line = f"{leading_ws}L  {row_name} "
            
            s[i] = new_line
            changed += 1
            # debug print
            print(f"Adjusted ROW line {i}: {row_name} now L ")

    if changed == 0:
        print(f"No ROW entries matched row='{row}' in ROW block (start={start}, end={end}).")
    return s

#This function is ment to find the UB for a certain variable such that we can make the bigM as strict as possible.
def find_bigM(row, s, cats):
     
    next_cat = find_following("COLUMNS", cats)
    start_of_column_block = cats.get("COLUMNS")
    
    start = start_of_column_block + 1
    end = cats[next_cat] if next_cat is not None else len(s)
    
    next_cat_bounds= find_following("BOUNDS", cats)
    start_of_bounds_block = cats.get("BOUNDS")
    
    start_bounds = start_of_bounds_block + 1
    end_bounds = cats[next_cat_bounds] if next_cat_bounds is not None else len(s)
    

    for i in range(start, end):
        line = s[i]
        
        if not line.strip():
            continue
        
        parts = toks(line)
         
        if len(parts) < 3:
            continue
        
        row_name = parts[1]

        if row_name == row:
            var = parts[0]
            for j in range(start_bounds, end_bounds):
                boundsline = s[j]
                if len(boundsline) < 4:
                    continue
                parts_bounds = toks(boundsline)
                relevant_var = parts_bounds[2]
                
                if (relevant_var ==var) and parts_bounds[0] == "UP":
                    print(f"Found upperbound for {relevant_var}: {toks(boundsline)[3]} ")
                    return toks(boundsline)[3],s, relevant_var
                elif (relevant_var ==var) and parts_bounds[0] == "LO":
                    if float(parts_bounds[3])<0:
                        new_line = f" LO BND1      {var}     0.000"
                        print(f"Adjusted lowerbound for {var} to 0")
                        s[j] = new_line
    return 10,s,var   
    
    
  
#This function is ment to add a row to the MILP to signal that a variable that was first bound to be non-negative by an indicator needs to be non-negative
#We also adjusted the LO to be 0.0 but sometimes that is not strict enough. 
#Inorder to add this constraint, we create a new GE row, add 0 as RHS and add the relevant variable to that row.                        
def add_row_nonnegativity(var,count, s, cats):
    
    row_name = f"N{str(count)}"
    
    next_cat = find_following("ROWS", cats)
    end = cats[next_cat] if next_cat is not None else len(s)
    #insert new ROW
    new_line = f" G  {row_name}"
    s.insert(end, new_line)
    cats = update_categories(cats, s)
    
    next_cat = find_following("RHS", cats)
    end = cats[next_cat] if next_cat is not None else len(s)
    #insert new RHS
    new_line = f"    RHS1      {row_name}        0"
    s.insert(end, new_line)
    cats = update_categories(cats, s)
    
    #find columns and add var row 1 in the RIGHT place!
    
    start_of_column_block = cats.get("COLUMNS")
    
    start = start_of_column_block + 1
    next_cat = find_following("COLUMNS", cats)
    end = cats[next_cat] if next_cat is not None else len(s)
    
    for i in range(start, end):
        line = s[i]
        
        if not line.strip():
            continue
        
        parts = toks(line)
         
        if len(parts) < 3:
            continue

        relevant_var = parts[0]
        
        if (relevant_var ==var):
            new_line =f"    {var}     {row_name}        1"
            s.insert(i, new_line)
            print(f"Inserted Column for {var} with name {row_name}")
            return s
    
    cats = update_categories(cats, s)
    return s
    
    
                   
        
def reformulate(fn_in, fn_out):
    s = open(fn_in, 'r', encoding='utf-8').read().splitlines()

    cats = {
        'INDICATORS': None,
        'ENDATA': None,
        'COLUMNS': None,
        'ROWS': None,
        'RHS': None,
        'BOUNDS': None,
        'MARKER': None
    }

    cats = update_categories(cats, s)

    indicator_block = s[cats['INDICATORS'] : cats['ENDATA'] + 1]  
    M = Decimal(10)
    count =0 
    for line in indicator_block:
        
        parts = toks(line)
        if len(parts) < 3:
            continue
        if parts[0].upper() == "IF":
     
            row = parts[1]
            variable = parts[2]
            M,s, var_affected = find_bigM(row, s, cats)
            s = adjust_rhs(row, M, 'RHS', cats, s)
            s = insert_column(variable,row, M, 'MARKER', cats, s)
            s = adjust_rows(row, 'ROWS', cats, s)
            s = add_row_nonnegativity(var_affected,count, s,cats)
            cats = update_categories(cats, s)

        count += 1
    start_idx = cats['INDICATORS']
    end_idx = cats['ENDATA']
    s = s[:start_idx] + s[end_idx:]

    open(fn_out, 'w', encoding='utf-8').write('\n'.join(s))
    print("wrote", fn_out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: script.py in.mps out.mps")
    else:
        reformulate(sys.argv[1], sys.argv[2])



