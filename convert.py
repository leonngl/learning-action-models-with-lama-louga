import os
import re

replace_list = ["init", "clear", "handempty", "on", "ontable", "and"]
problems_path = "./problems"


for fname in os.listdir("./problems/"):
    fpath = os.path.join(problems_path, fname)
    problem_num = fname[11:]

    with open(fpath, "r") as file:
        content = file.read()
    
    for replace_str in replace_list:
        content = re.sub(replace_str, replace_str, content, flags=re.IGNORECASE)
        content = re.sub(r"\(:objects([\w\s]*)\)", r"(:objects\1 - block)", content)
    

    with open(fpath, "w") as file:
        file.write(content)

    os.rename(fpath, os.path.join(problems_path, f"problem{problem_num}"))
    