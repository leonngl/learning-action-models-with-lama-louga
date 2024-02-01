import itertools
from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader, PDDLWriter
import pygad

problems = ["4-0", "4-1", "4-2", "5-0"]

#read domain and plans
# delete action preconds and effects in model
reader = PDDLReader()
domain = reader.parse_problem("domain.pddl")


# compute final states
final_states = []
state_lens = []
for problem_str in problems:
    with open(f"./problems/problem{problem_str}.pddl") as f:
        problem_content = f.read()
    
    problem = reader.parse_problem("domain.pddl", f"./problems/problem{problem_str}.pddl")
    plan = reader.parse_plan(problem, f"./plans/plan-{problem_str}.txt")
    state = [f for (f, v) in problem.initial_values.items() if v.is_true()]
    init_state = state

    with open(f"./trajectories/trajectory{problem_str}", "w") as f:
        f.write("(trajectory\n\n")
        f.write("(:objects")
        for o in problem.all_objects:
            f.write(f" {o.name} -  object")
        f.write(" )\n\n")
        f.write("(:init")
        for s in init_state:
            s_str = str(s).replace("(", " ").replace(")", "").replace(",", "")
            f.write(" (" + s_str + ")")
        f.write(")\n\n")

        for action_instance in plan.actions:
            a_str = str(action_instance).replace("(", " ").replace(")", "").replace(",", "")
            f.write(f"(:action ({a_str}))\n\n")

            action = action_instance.action
            object_param_map = {action.parameters[i].name : o for (i, o) in enumerate(action_instance.actual_parameters)}
            for effect in action.effects:
                effect_fluent = effect.fluent
                predicate = effect_fluent.fluent()
                param_predicate = predicate(*[object_param_map[str(o)] for o in effect_fluent.args])
                if effect.value.is_true():
                    if param_predicate not in state:
                        state.append(param_predicate)
                else:
                    if param_predicate in state:
                        state.remove(param_predicate)
            
            f.write("(:state")
            for s in state:
                s_str = str(s).replace("(", " ").replace(")", "").replace(",", "")
                f.write(" (" + s_str + ")")
            f.write(")\n\n")
        f.write(")")

    
