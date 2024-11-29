import random
import requests
import threading
import time
from deap import base, creator, tools, algorithms
from concurrent.futures import Executor, Future


class KubernetesSimulatorExecutor(Executor):
    def __init__(self, container_endpoints):
        self.container_endpoints = container_endpoints
        self.lock = threading.Lock()

    def submit(self, fn, *args, **kwargs):
        future = Future()
        threading.Thread(target=self._run_simulation, args=(future, fn, *args), kwargs=kwargs).start()
        return future

    def _run_simulation(self, future, fn, *args, **kwargs):
        try:
            container = self._get_available_container()
            result = fn(container, *args, **kwargs)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)

    def _get_available_container(self):
        with self.lock:
            # Rotate endpoint in a round-robin fashion
            endpoint = self.container_endpoints.pop(0)
            self.container_endpoints.append(endpoint)
            return endpoint

    def map(self, fn, *iterables, timeout=None, chunksize=1):
        futures = [self.submit(fn, *args) for args in zip(*iterables)]
        return [future.result(timeout=timeout) for future in futures]

def run_simulation(container_endpoint, params):
    # Send parameters to start the simulation
    response = requests.post(f"{container_endpoint}/run_simulation", json=params)
    response.raise_for_status()
    job_id = response.json().get("job_id")

    # Poll for the result
    while True:
        result_response = requests.get(f"{container_endpoint}/result/{job_id}")
        if result_response.status_code == 200:
            return result_response.json().get("result")  # Return the final result
        time.sleep(0.5)  # Poll every 0.5 seconds

# DEAP setup for a simple genetic algorithm
creator.create("FitnessMax", base.Fitness, weights=(1.0,))  # Maximizing fitness
creator.create("Individual", list, fitness=creator.FitnessMax)

def individual_to_params(individual):
    return {"param1": individual[0], "param2": individual[1]}
            
# Define DEAP's toolbox with the genetic operators
toolbox = base.Toolbox()
toolbox.register("attr_float", random.uniform, -10, 10)
toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_float, n=2)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("mate", tools.cxBlend, alpha=0.5)
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.2)
toolbox.register("select", tools.selTournament, tournsize=3)

# Initialize container endpoints and KubernetesSimulatorExecutor
container_endpoints = [
    "http://localhost:5000",
    "http://localhost:5001",
    "http://localhost:5002"
]
executor = KubernetesSimulatorExecutor(container_endpoints)

def main():
    random.seed(64)
    pop = toolbox.population(n=10)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: sum(f[0] for f in x) / len(x))
    stats.register("min", lambda x: min(f[0] for f in x))
    stats.register("max", lambda x: max(f[0] for f in x))

    # Evaluate the initial population
    for ind in pop:
        ind.fitness.values = (0,)  # Initialize fitness

    # Evolve the population
    for gen in range(5):  # For 5 generations
        # Select the next generation individuals
        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))

        # Apply crossover and mutation
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < 0.5:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values
        for mutant in offspring:
            if random.random() < 0.2:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        # Evaluate the individuals with invalid fitness using the executor
        invalid_individuals = [ind for ind in offspring if not ind.fitness.valid]
        param_list = [individual_to_params(ind) for ind in invalid_individuals]
        fitnesses = executor.map(run_simulation, param_list)

        for ind, fit in zip(invalid_individuals, fitnesses):
            ind.fitness.values = (fit,)

        # Replace population with the new generation
        pop[:] = offspring

        # Update the statistics and hall of fame
        hof.update(pop)
        record = stats.compile(pop)
        print(f"Generation {gen}: {record}")

    return pop, hof

if __name__ == "__main__":
    pop, hof = main()
    print("Best individual is:", hof[0], hof[0].fitness.values)
