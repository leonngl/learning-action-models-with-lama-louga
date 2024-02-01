import itertools
from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader, PDDLWriter
import pygad

# 4-3, 4-1, 4-2, 5-0, 6-0

problems = ["4-3", "4-1", "4-2", "5-0", "6-0"]
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
    state_lens.append(len(problem.initial_values))

    for action_instance in plan.actions:
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
    
    final_states.append(state)
        

genome_encoding = []
possible_gene_vals = {}
for action in domain.actions:
    num_params = len(action.parameters)
    for predicate in domain.fluents:
        for perm in itertools.product(["x", "y"][:num_params], repeat=predicate.arity):
            parameters = [action.parameter(p) for p in perm]
            action_pred_tuple = (action.name, predicate(*parameters))
            genome_encoding.append(action_pred_tuple)
            possible_gene_vals[action_pred_tuple] = {0, 1, 2}


for i, p in enumerate(genome_encoding, 1):
    print(f"{i} : {p}")



def compute_usable_predicates(params):
    res = []
    for predicate in domain.fluents:
        for perm in itertools.product(params, repeat=predicate.arity):
            res.append(predicate(*perm))
    
    return res

# create genetic encoding
# dict of type (action, parameterized predicate)

# algo to reduce number of possible genomes
# create list of invalid genomes, assign them fitness of zero
for problem_str in problems:
    problem = reader.parse_problem("domain.pddl", f"./problems/problem{problem_str}.pddl")
    plan = reader.parse_plan(problem, f"./plans/plan-{problem_str}.txt")

    Q = {f for (f, v) in problem.initial_values.items() if v.is_true()}
    R = set()
    for action_instance in plan.actions:
        action = action_instance.action
        # compute predicates that could be used 
        usable_predicates = compute_usable_predicates(action_instance.actual_parameters)
        object_param_map = {o : action.parameters[i] for (i, o) in enumerate(action_instance.actual_parameters)}
        for p in usable_predicates:
            predicate = p.fluent()
            params = [object_param_map[o] for o in p.args]
            if p in Q:
                possible_gene_vals[(action.name, predicate(*params))].discard(1)
                R.add(p)
                Q.remove(p)
            elif p not in R:
                possible_gene_vals[(action.name, predicate(*params))].discard(2)
                R.add(p)

gene_space = [list(possible_gene_vals[tpl]) for tpl in genome_encoding]


def compute_problem_from_genome(genome):
    gen_domain = reader.parse_problem("domain.pddl")
    for action in gen_domain.actions:
        action.clear_preconditions()
        action.clear_effects()
    for i, gene in enumerate(genome):
        action_name, predicate = genome_encoding[i]
        if gene not in possible_gene_vals[(action_name, predicate)]:
            return None
        if gene == 1:
            gen_domain.action(action_name).add_effect(predicate, True)
        if gene == 2:
            gen_domain.action(action_name).add_effect(predicate, False)
    
    return gen_domain





# fitness function
def fitness_func(ga_instance, genome, genome_idx):
    # if genome not in possible vals set fitness to zero
    gen_domain = compute_problem_from_genome(genome)
    if not gen_domain:
        return 0
    
    num_adds_dels = 0
    error_add = 0
    error_del = 0
    total_obs = 0
    obs_error = 0

    for i, problem_str in enumerate(problems):
        with open(f"./problems/problem{problem_str}.pddl") as f:
            problem_content = f.read()
        
        domain_str = PDDLWriter(gen_domain).get_domain()
        domain_str = domain_str.replace("pick_up", "pick-up")
        domain_str = domain_str.replace("put_down", "put-down")
        problem = reader.parse_problem_string(domain_str, problem_content)
        plan = reader.parse_plan(problem, f"./plans/plan-{problem_str}.txt")
        state = [f for (f, v) in problem.initial_values.items() if v.is_true()]

        for action_instance in plan.actions:
            action = action_instance.action
            object_param_map = {action.parameters[i].name : o for (i, o) in enumerate(action_instance.actual_parameters)}
            for effect in action.effects:
                num_adds_dels += 1
                effect_fluent = effect.fluent
                predicate = effect_fluent.fluent()
                param_predicate = predicate(*[object_param_map[str(o)] for o in effect_fluent.args])
                if effect.value.is_true():
                    if param_predicate in state:
                        error_add += 1
                    else:
                        state.append(param_predicate)
                else:
                    if param_predicate not in state:
                        error_del += 1
                    else:
                        state.remove(param_predicate)
        
        # compute error from difference of state to goal state
        state_set = set(state)
        goal_set = set(final_states[i])
        obs_error += len(state_set - goal_set) + len(goal_set - state_set)
        total_obs += state_lens[i]


    return (1 - (error_del + error_add) / num_adds_dels) * (1 - obs_error/total_obs)
                    

ideal_encoding = []
for action, pred in genome_encoding:
    effect_fluent_dict = {e.fluent : e for e in domain.action(action).effects}
    if pred in effect_fluent_dict.keys():
            if effect_fluent_dict[pred].value.is_true():
                    ideal_encoding.append(1)
            else:
                    ideal_encoding.append(2)
    else:
            ideal_encoding.append(0)

gen_domain = compute_problem_from_genome(ideal_encoding)
print(fitness_func(None, ideal_encoding, None))

# run genetic algo


ga_instance = pygad.GA(
                        num_generations=10,
                       num_parents_mating=2,
                       fitness_func=fitness_func,
                       sol_per_pop=15,
                       num_genes=len(genome_encoding),
                       gene_space=gene_space
                      )

print("Run")
ga_instance.run()


best_genome = None
best_fitness = 0
for genome in ga_instance.population:
    fitness = fitness_func(None, genome, None)
    if fitness > best_fitness:
        best_genome = genome
    print(f"{genome} : {fitness}")

print(best_genome)
print(ideal_encoding)

best_domain = compute_problem_from_genome(best_genome)


# compute preconditions
Y = {tpl : 0 for tpl in genome_encoding}
N = {tpl : 0 for tpl in genome_encoding}

for problem_str in problems:
    with open(f"./problems/problem{problem_str}.pddl") as f:
            problem_content = f.read()
        
    domain_str = PDDLWriter(best_domain).get_domain()
    domain_str = domain_str.replace("pick_up", "pick-up")
    domain_str = domain_str.replace("put_down", "put-down")
    problem = reader.parse_problem_string(domain_str, problem_content)
    plan = reader.parse_plan(problem, f"./plans/plan-{problem_str}.txt")

    with SequentialSimulator(problem=problem) as simulator:
        state = simulator.get_initial_state()
        for action_instance in plan.actions:
            action = action_instance.action
            usable_predicates = compute_usable_predicates(action_instance.actual_parameters)
            object_param_map = {o : action.parameters[i] for (i, o) in enumerate(action_instance.actual_parameters)}
            for p in usable_predicates:
                predicate = p.fluent()
                params = [object_param_map[o] for o in p.args]
                if state.get_value(p).is_true():
                    Y[(action.name, predicate(*params))] += 1
                else:
                    N[(action.name, predicate(*params))] += 1
                
            state = simulator.apply(state, action_instance)


for i, action_pred_tuple in enumerate(genome_encoding):
    action_name, predicate = action_pred_tuple
    action = best_domain.action(action_name)
    if best_genome[i] == 0:
        if N[action_pred_tuple] == 0 and Y[action_pred_tuple] > 0:
            action.add_precondition(predicate)
        elif N[action_pred_tuple] > 0 and Y[action_pred_tuple] == 0:
            action.add_precondition(Not(predicate))
    elif best_genome[i] == 1:
            action.add_precondition(Not(predicate))
    elif best_genome[i] == 2:
            action.add_precondition(predicate)

PDDLWriter(best_domain).write_domain(f"./genetic_learned_domains/learned_domain-{"_".join(problems)}")


