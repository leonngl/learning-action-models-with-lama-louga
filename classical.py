from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader, PDDLWriter
from unified_planning.model import Fluent
import itertools

# input
# 4-3, 4-1, 4-2, 5-0, 6-0
problems = ["4-3", "4-1"]#, "4-2", "5-0", "6-0"]


reader = PDDLReader()

domain = reader.parse_problem("./domain.pddl", f"./problems/problem{problems[0]}.pddl")
block_type = domain.user_types[0]
step_type = UserType("step")

# add objects
max_step = 0
plan_lens = []
final_states = []
all_objects = set()
for problem_str in problems:
    problem = reader.parse_problem("./domain.pddl", f"./problems/problem{problem_str}.pddl")
    all_objects |= set(problem.all_objects)
    for object in problem.all_objects:
        if not domain.has_object(object.name):
            domain.add_object(object.name, block_type)

    plan = reader.parse_plan(problem, f"./plans/plan-{problem_str}.txt", )
    with open(f"./plans/plan-{problem_str}.txt", "r") as f:
        plan_len = sum(1 for _ in f)
        max_step = max(max_step, plan_len)
        plan_lens.append(plan_len)
    
max_step = max(max_step + 1, len(problems))   # +1 to ensure we can apply last operation of plan 

for problem_str in problems:
    problem = reader.parse_problem("./domain.pddl", f"./problems/problem{problem_str}.pddl")
    plan = reader.parse_plan(problem, f"./plans/plan-{problem_str}.txt", )
    problem.add_objects(all_objects - set(problem.all_objects))

    with SequentialSimulator(problem=problem) as simulator:
        state = simulator.get_initial_state()
        for action in plan.actions:
            state = simulator.apply(state, action)
        if not simulator.is_goal(state):
            raise RuntimeError("Plan didn't reach goal.")
        final_states.append(state)
    


num_objects = len(domain.all_objects)
domain.clear_goals()
orig_fluents = domain.fluents.copy()
orig_actions = domain.actions.copy()
domain.clear_actions()
instantiated_orig_fluents = [f for f in domain.initial_values.keys()]
assert(len(instantiated_orig_fluents) == (num_objects * (3 + num_objects) + 1))
    
# mode-prog fluent
mode_prog = domain.add_fluent("mode_prog", default_initial_value=True)


# add predicates for steps
at_fluent = domain.add_fluent("at", i=step_type)
next_fluent = domain.add_fluent("next", i=step_type, j=step_type)

for action in orig_actions:
    num_params = len(action.parameters)
    variables_dict = {f"b{i}" : block_type for i in range(1, num_params + 1)}
    variables = list(variables_dict.keys())
    apply_action = InstantaneousAction(f"apply_{action.name}", **variables_dict, cur_step=step_type, next_step=step_type)
    apply_action.add_effect(mode_prog, False, condition=mode_prog)

    # fluent for plan step
    plan_fluent = domain.add_fluent(f"plan_{action.name}", **variables_dict, i=step_type,)
    cur_step_param = apply_action.parameter("cur_step")
    next_step_param = apply_action.parameter("next_step")
    block_params = [apply_action.parameter(f"b{i}") for i in range(1, num_params + 1)]
    apply_action.add_precondition(at_fluent(cur_step_param))
    apply_action.add_precondition(plan_fluent(*block_params, cur_step_param))
    apply_action.add_precondition(next_fluent(cur_step_param, next_step_param))

    apply_action.add_effect(at_fluent(cur_step_param), False)
    apply_action.add_effect(at_fluent(next_step_param), True)

    for predicate in [fluent for fluent in orig_fluents if fluent.type.is_bool_type()]:

        for perm in itertools.product(variables, repeat=predicate.arity):
            suffix = f"_{predicate.name}_{action.name}{"_" if len(perm) > 0 else ""}{"_".join(perm)}"
            pre_fluent = domain.add_fluent("pre" + suffix, default_initial_value=True)
            add_fluent = domain.add_fluent("add" + suffix, default_initial_value=False)
            del_fluent = domain.add_fluent("del" + suffix, default_initial_value=False)

            # action to remove precondition
            pre_action = InstantaneousAction("program_pre" + suffix)
            pre_action.add_precondition(And(Not(del_fluent), Not(add_fluent), mode_prog, pre_fluent))
            pre_action.add_effect(pre_fluent, False)
            domain.add_action(pre_action)
            # action to add negative or positive effect
            effect_action = InstantaneousAction("program_eff" + suffix)
            effect_action.add_precondition(And(Not(del_fluent), Not(add_fluent), mode_prog))
            effect_action.add_effect(del_fluent, True, condition=pre_fluent)
            effect_action.add_effect(add_fluent, True, condition=Not(pre_fluent))
            domain.add_action(effect_action)
            

            # preconditions for apply effect
            permuted_params = [apply_action.parameter(param_str) for param_str in perm]
            parameterized_predicate = predicate(*permuted_params)
            apply_action.add_precondition(Implies(pre_fluent, parameterized_predicate))
            apply_action.add_effect(parameterized_predicate, True, condition=add_fluent)
            apply_action.add_effect(parameterized_predicate, False, condition=del_fluent)
    domain.add_action(apply_action)


# actions for validating example
# assert that problem has plan
t = 1
test_fluents = []
filtered_problems = []
for problem_str in problems:
    filepath = f"./plans/plan-{problem_str}.txt"
    with open(filepath, "r") as f:
        if "NO PLAN FOUND" in f.read():
            print(f"Skipping problem {problem_str}.")
            continue
    
    filtered_problems.append(problem_str)

    test_fluent = Fluent(f"test_{t}")
    test_fluents.append(test_fluent)

    domain.add_fluent(test_fluent, default_initial_value=False)
    # add to goal
    domain.add_goal(test_fluent)
    t += 1


steps = []
prev_step_object = domain.add_object(Object(f"i1", step_type))
steps.append(prev_step_object)
domain.set_initial_value(at_fluent(prev_step_object), True)
next_fluent = domain.fluent("next")
for i in range(2, max_step + 2):
    step_object = domain.add_object(Object(f"i{i}", step_type))
    steps.append(step_object)
    domain.set_initial_value(next_fluent(prev_step_object, step_object), True)
    prev_step_object = step_object


prev_validate_action = None
for i, problem_str in enumerate(filtered_problems):
    t = i + 1
    filepath = f"./plans/plan{problem_str}"
    
    # load problem
    problem = reader.parse_problem("domain.pddl", f"./problems/problem{filtered_problems[i]}.pddl")


    # validate actions
    validate_action = InstantaneousAction(f"validate_{t}")
    

    for fluent in instantiated_orig_fluents:
        if final_states[i].get_value(fluent).is_true():
            validate_action.add_precondition(fluent)
        else:
            validate_action.add_precondition(Not(fluent))
    
    if i > 0:
        validate_action.add_precondition(And(*test_fluents[:i]))
    #validate_action.add_precondition(Not(Or(*test_fluents[i:])))
    validate_action.add_precondition(And(*list(map(Not, test_fluents[i:]))))
    validate_action.add_precondition(Not(mode_prog))
    validate_action.add_effect(test_fluents[i], True)

    # set the effect for previous action
    true_initials = [f for (f, v) in problem.initial_values.items() if v.is_true()]
    if i != 0:
        for fluent in [f for f in instantiated_orig_fluents if f not in true_initials]:
            prev_validate_action.add_effect(fluent, False)
        for fluent in true_initials:
            prev_validate_action.add_effect(fluent, True)

    if i == len(filtered_problems) - 1: # shouldn't matter
        for fluent in instantiated_orig_fluents:
            validate_action.add_effect(fluent, False)


    # add effect for validate action
    validate_action.add_precondition(at_fluent(steps[plan_lens[i]])) # this overshoots!
    validate_action.add_effect(at_fluent(steps[0]), True)
    validate_action.add_effect(at_fluent(steps[plan_lens[i]]), False)
    
    domain.add_action(validate_action)

    # validate i deletes plan fluents of plan i, and sets plan fluents of plan i + 1
    with open(f"./plans/plan-{problem_str}.txt", "r") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip("()\n")
            parts = line.split(" ")
            action_name = parts[0]
            plan_fluent = domain.fluent(f"plan_{action_name}")
            step_object = domain.object(f"i{i}")

            for object in parts[1:]:
                if prev_validate_action is not None:
                    prev_validate_action.add_effect(plan_fluent(*[domain.object(obj_name) for obj_name in parts[1:]], step_object), True)
                validate_action.add_effect(plan_fluent(*[domain.object(obj_name) for obj_name in parts[1:]], step_object), False)

    prev_validate_action = validate_action






with open(f"./plans/plan-{problems[0]}.txt", "r") as f:
    for i, line in enumerate(f, start=1):
        line = line.strip("()\n")
        parts = line.split(" ")
        action_name = parts[0]
        for object in parts[1:]:
            plan_fluent = domain.fluent(f"plan_{action_name}")
            step_object = domain.object(f"i{i}")
            domain.set_initial_value(plan_fluent(*[domain.object(obj_name) for obj_name in parts[1:]], step_object), True)



writer = PDDLWriter(domain)
writer.write_domain(f"./learning-problems/learn_domain_{"_".join(problems)}.pddl")      
writer.write_problem(f"./learning-problems/learn_problem_{"_".join(problems)}.pddl")      


#planner = OneshotPlanner(name="fast-downward")
#result = planner.solve(domain)
#print(result)


