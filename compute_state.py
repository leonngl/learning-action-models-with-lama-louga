from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader, PDDLWriter
from unified_planning.model import Fluent
import itertools

import sys


reader = PDDLReader()

domain = reader.parse_problem("./domain.pddl")
block_type = domain.user_types[0]


orig_fluents = domain.fluents.copy()
orig_actions = domain.actions.copy()

for action in orig_actions:
    num_params = len(action.parameters)
    variables_dict = {f"b{i}" : block_type for i in range(1, num_params + 1)}
    variables = list(variables_dict.keys())
    

    for predicate in [fluent for fluent in orig_fluents if fluent.type.is_bool_type()]:

        for perm in itertools.product(variables, repeat=predicate.arity):
            suffix = f"_{predicate.name}_{action.name}{"_" if len(perm) > 0 else ""}{"_".join(perm)}"
            pre_fluent = domain.add_fluent("pre" + suffix, default_initial_value=True)
            add_fluent = domain.add_fluent("add" + suffix, default_initial_value=False)
            del_fluent = domain.add_fluent("del" + suffix, default_initial_value=False)

            # action to remove precondition
            pre_action = InstantaneousAction("program_pre" + suffix)
            pre_action.add_precondition(And(Not(del_fluent), Not(add_fluent), pre_fluent))
            pre_action.add_effect(pre_fluent, False)
            domain.add_action(pre_action)
            # action to add negative or positive effect
            effect_action = InstantaneousAction("program_eff" + suffix)
            effect_action.add_precondition(And(Not(del_fluent), Not(add_fluent)))
            effect_action.add_effect(del_fluent, True, condition=pre_fluent)
            effect_action.add_effect(add_fluent, True, condition=Not(pre_fluent))
            domain.add_action(effect_action)

fluent_dict = {f.fluent().name : f for f in domain.initial_values.keys()}



#if __name__ == "__main__":
#    filepath = sys.argv[1]

filepath = "out.txt"

# strip plan
plan_str = []
with open(filepath, "r") as f:
    for line in f:
        if (not "apply" in line) and (not "validate" in line):
            plan_str.append(line)

plan = reader.parse_plan_string(domain, "".join(plan_str))

with SequentialSimulator(problem=domain) as simulator:
    state = simulator.get_initial_state()
    for action in plan.actions:
        state = simulator.apply(state, action)



print([f for (f, _) in domain.initial_values.items() if state.get_value(f).is_true()])
#print(state)

pred_dict = {
    "pick-up" : ["pre_clear_pick-up_b1",
                 "pre_ontable_pick-up_b1",
                 "pre_handempty_pick-up",
                 "del_ontable_pick-up_b1",
                 "del_clear_pick-up_b1",
                 "del_handempty_pick-up",
                 "add_holding_pick-up_b1"
                 ],
    "put-down" : [
        "pre_holding_put-down_b1",
        "del_holding_put-down_b1",
        "add_clear_put-down_b1",
        "add_handempty_put-down",
        "add_ontable_put-down_b1"
    ],
    "stack" : [
        "pre_holding_stack_b1",
        "pre_clear_stack_b2",
        "del_holding_stack_b1",
        "del_clear_stack_b2",
        "add_handempty_stack",
        "add_clear_stack_b1",
        "add_on_stack_b1_b2"
    ],
    "unstack" : [
        "pre_on_unstack_b1_b2",
        "pre_clear_unstack_b1",
        "pre_handempty_unstack",
        "add_holding_unstack_b1",
        "add_clear_unstack_b2",
        "del_clear_unstack_b1",
        "del_handempty_unstack",
        "del_on_unstack_b1_b2"
    ]
}
        
  

metrics = {}
avg_recall = 0
avg_precision = 0
for action in orig_actions:
    num_params = len(action.parameters)
    variables_dict = {f"b{i}" : block_type for i in range(1, num_params + 1)}
    variables = list(variables_dict.keys())
    
    tp = 0
    fp = 0
    fn = 0


    for predicate in [fluent for fluent in orig_fluents if fluent.type.is_bool_type()]:

        for perm in itertools.product(variables, repeat=predicate.arity):
            suffix = f"_{predicate.name}_{action.name}{"_" if len(perm) > 0 else ""}{"_".join(perm)}"

            for fluent_str in [prefix + suffix for prefix in ("pre", "add", "del")]:
                if fluent_str in pred_dict[action.name]:
                    if state.get_value(fluent_dict[fluent_str]).is_true():
                        tp += 1
                    else:
                        fn += 1
                elif state.get_value(fluent_dict[fluent_str]).is_true(): #and not fluent_str.startswith("pre"):
                    fp += 1
    
    recall = 0 if (tp == 0 and fn == 0) else tp/(tp + fn)
    precision = 0 if (tp == 0 and fp == 0) else tp/(tp + fp)
    avg_recall += recall
    avg_precision += precision
    metrics[action.name] = {"tp" : tp, "fp" : fp, "fn" : fn, "recall" : recall, "prec" : precision}


#print(state)
print("\n\n")
print(metrics)
print(avg_recall / 4)
print(avg_precision / 4)








