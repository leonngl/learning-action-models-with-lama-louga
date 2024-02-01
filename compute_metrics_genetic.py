from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader
import sys
import os

file = "./genetic_learned_domains/learned_domain-4-3_4-1_4-2_5-0_6-0"
reader = PDDLReader()
with open(os.path.join(os.getcwd(), file)) as f:
    learned_domain_string = f.read()

learned_domain_string = learned_domain_string.replace("pick_up", "pick-up")
learned_domain_string = learned_domain_string.replace("put_down", "put-down")

learned_domain = reader.parse_problem_string(learned_domain_string)
domain = reader.parse_problem("domain.pddl")

avg_recall = 0
avg_precision = 0
metrics = {}

for action in domain.actions:
    actual_preconditions = set(action.preconditions[0].args)
    actual_add_effects = set([eff for eff in action.effects if eff.value.is_true()])
    actual_del_effects = set([eff for eff in action.effects if eff.value.is_false()])
    learned_action = learned_domain.action(action.name)
    learned_preconditions = set(learned_action.preconditions[0].args)
    positive_preconditions = set([p for p in list(learned_preconditions) if not p.is_not()])
    learned_add_effects = set([eff for eff in learned_action.effects if eff.value.is_true()])
    learned_del_effects = set([eff for eff in learned_action.effects if eff.value.is_false()])

    tp = 0
    fp = 0
    fn = 0

    tp = len(actual_preconditions & learned_preconditions) \
            + len(actual_add_effects & learned_add_effects) \
            + len(actual_del_effects & learned_del_effects) \

    fp = len(learned_add_effects - actual_add_effects) \
            + len(learned_del_effects - actual_del_effects) \
            + len(positive_preconditions - actual_preconditions) \

    fn = len(actual_preconditions - learned_preconditions) \
            + len(actual_add_effects - learned_add_effects) \
            + len(actual_del_effects - learned_del_effects) \

    recall = tp/(tp + fn)
    precision = tp/(tp + fp)
    avg_recall += recall
    avg_precision += precision
    metrics[action.name] = {"tp" : tp, "fp" : fp, "fn" : fn, "recall" : (tp/(tp + fn)), "prec" : (tp/(tp + fp))}

print(metrics)
print(avg_recall / 4)
print(avg_precision / 4)


        
