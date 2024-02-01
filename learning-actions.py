from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader, PDDLWriter


problems = ["4-3"]

reader = PDDLReader()

planner = OneshotPlanner(name="fast-downward")

for problem_str in problems:
    problem = reader.parse_problem("domain.pddl", f"./problems/problem{problem_str}.pddl")

    result = planner.solve(problem)

    filepath = f"./plans/plan-{problem_str}.txt"
    if result.status == up.engines.PlanGenerationResultStatus.SOLVED_SATISFICING:
        writer = PDDLWriter(problem)
        writer.write_plan(result.plan, filepath)
    else:
        with open(filepath, "w") as f:
            f.write("NO PLAN FOUND")