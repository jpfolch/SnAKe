import torch
from gp_utils import BoTorchGP
from functions import SnAr
from snake import SnAKe, RandomTSP
from bayes_op import UCBwLP, oneExpectedImprovement, oneProbabilityOfImprovement, EIperUnitCost, TruncatedExpectedImprovement
from temperature_env import NormalDropletFunctionEnv
from cost_functions import max_time_cost, max_time_cost_torch
import numpy as np
import sys
import os

'''
This script was used to get the synchronous SnAr experiment results.

To reproduce any run, type:

python experiment_async 'method' 'run_number' 'budget' 'epsilon'

Where:

method - 'SnAKe', 'EI', 'UCB', 'PI', 'Random', 'EIpu', 'TrEI'
run number - any integer, in experiments we used 1-10 inclusive
budget - integer in [100, 250]
epsilon - integer [0, 0.1, 1.0], alternatively modify the script to set epsilon = 'lengthscale' for ell-SnAKe
'''

method = str(sys.argv[1])
run_num = int(sys.argv[2])
budget = int(sys.argv[3])
epsilon = float(sys.argv[4])
gamma = 1

function_number = 0

if budget == 0:
    budget = 10
elif budget == 1:
    budget = 25
elif budget == 2:
    budget = 50
else:
    budget = 100

if epsilon == 100:
    epsilon = 'lengthscale'

print(method, run_num, budget, epsilon)

# Make sure problem is well defined
assert method in ['SnAKe', 'EI', 'UCB', 'PI', 'Random', 'EIpu'], 'Method must be string in [SnAKe, EI, UCB, PI, Random, EIpu]'
assert budget in [10, 25, 50, 100], \
    'Budget must be integer in [10, 25, 50, 100]'
assert epsilon in [0, 0.1, 0.25, 1, 'lengthscale'], \
    'Epsilon must be in [0, 0.1, 0.25, 1]'

# Define function name
functions = [SnAr()]
func = functions[function_number]

# We start counting from zero, so set budget minus one
budget = budget - 1

# Define cost function
cost_function = lambda x, y: max_time_cost(x, y)

# Define seed, sample initalisation points
seed = run_num + (function_number + 1) * 91
torch.manual_seed(seed)
np.random.seed(seed)

dim = func.t_dim
if func.x_dim is not None:
    dim = dim + func.x_dim

initial_temp = np.random.uniform(size = (1, dim)).reshape(1, -1)

x_train = np.random.uniform(0, 1, size = (max(int(budget / 5), 10 * dim), dim))
y_train = []
for i in range(0, x_train.shape[0]):
    y_train.append(func.query_function(x_train[i, :].reshape(1, -1)))

y_train = np.array(y_train)

# Train and set educated guess of hyper-parameters
gp_model = BoTorchGP(lengthscale_dim = dim)

gp_model.fit_model(x_train, y_train)
gp_model.optim_hyperparams()

hypers = gp_model.current_hyperparams()
init_max_value = hypers[-1]

print('Initial hyper-parameters:', hypers)
# Define Normal BayesOp Environment without delay
env = NormalDropletFunctionEnv(func, budget, max_batch_size = 1)

# Choose the correct method
if method == 'SnAKe':
    mod = SnAKe(env, merge_method = 'e-Point Deletion', merge_constant = epsilon, cost_function = cost_function, initial_temp = initial_temp, \
        hp_update_frequency = 25)
elif method == 'EI':
    mod = oneExpectedImprovement(env, initial_temp = initial_temp, hp_update_frequency = 25)
elif method == 'UCB':
    mod = UCBwLP(env, initial_temp = initial_temp, hp_update_frequency = 25)
elif method == 'PI':
    mod = oneProbabilityOfImprovement(env, initial_temp = initial_temp, hp_update_frequency = 25)
elif method == 'Random':
    mod = RandomTSP(env, initial_temp = initial_temp)
elif method == 'EIpu':
    cost_function = max_time_cost_torch
    mod = EIperUnitCost(env, initial_temp = initial_temp, cost_constant = 1, cost_equation = cost_function)
elif method == 'TrEI':
    mod = TruncatedExpectedImprovement(env, initial_temp = initial_temp)

mod.set_hyperparams(constant = hypers[0], lengthscale = hypers[1], noise = hypers[2], mean_constant = hypers[3], \
            constraints = True)

X, Y = mod.run_optim(verbose = True)

print(X)
print(np.array(Y))

if epsilon == 'lengthscale':
    epsilon = 'l'

if method == 'SnAKe':
    folder_inputs = 'experiment_results_snar_residence_time/' + f'{epsilon}-EaS/' + f'/budget{budget + 1}/' + '/inputs/'
    folder_outputs = 'experiment_results_snar_residence_time/' + f'{epsilon}-EaS/' + f'/budget{budget + 1}/' + '/outputs/'
    file_name = f'run_{run_num}'
elif method == 'Random':
    folder_inputs = 'experiment_results_snar_residence_time/' + f'Random/' + f'/budget{budget + 1}/' + '/inputs/'
    folder_outputs = 'experiment_results_snar_residence_time/' + f'Random/' + f'/budget{budget + 1}/' + '/outputs/'
    file_name = f'run_{run_num}'
elif method == 'EIpu':
    folder_inputs = 'experiment_results_snar_residence_time/' + str(gamma) + f'EIpu/' + f'/budget{budget + 1}/' + '/inputs/'
    folder_outputs = 'experiment_results_snar_residence_time/' + str(gamma) + f'EIpu/' + f'/budget{budget + 1}/' + '/outputs/'
    file_name = f'run_{run_num}'
else:
    folder_inputs =  'experiment_results_snar_residence_time/' + method + '/' + f'/budget{budget + 1}/inputs/'
    folder_outputs =  'experiment_results_snar_residence_time/' + method + '/' + f'/budget{budget + 1}/outputs/'
    file_name = f'run_{run_num}'

# create directories if they exist
os.makedirs(folder_inputs, exist_ok = True)
os.makedirs(folder_outputs, exist_ok = True)

print(X.shape[0])
print(np.array(Y).shape[0])

np.save(folder_inputs + file_name, X)
np.save(folder_outputs + file_name, np.array(Y))