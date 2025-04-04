import networkx as nx
import numpy as np
from scm import noises as noise_utils
from utils import io


def _evaluate_function(f_str, data_dict, n_samples):
    """
    Evaluate lambda string on sample-wise data_dict.
    Returns an array of length n_samples.
    """
    import re
    match = re.match(r'lambda\s*(.*?):', f_str)
    args = match.group(1).replace('(', '').replace(')', '').strip().split(',')
    args = [arg.strip() for arg in args if arg.strip() != '_']

    f = eval(f_str)

    result = np.zeros(n_samples)
    for i in range(n_samples):
        input_vals = [data_dict[arg][i] for arg in args]
        result[i] = f(*input_vals)
    return result


def sample_L1(scm, n_samples):
    """
    Observational data: simulate from the full SCM.
    """
    noise_data = {}
    data = {}

    for X_j in scm.G.nodes:
        noise_dist = noise_utils.generate_distribution(scm.N[X_j])
        noise_data[X_j] = noise_dist(n_samples)

    for X_j in nx.topological_sort(scm.G):
        if scm.G.in_degree(X_j) == 0:
            data[X_j] = noise_data[X_j]
        else:
            f_j = scm.F[X_j]
            # result = _evaluate_function(f_j, data)
            result = _evaluate_function(f_j, data, n_samples)
            data[X_j] = result + noise_data[X_j]

    return data


def sample_L2(scm, n_samples, interventions):
    """
    Interventional data: simulate from SCM with fixed values for a subset of variables.
    """
    do_dict = io.parse_interventions(interventions)
    scm.intervene(do_dict)

    noise_data = {}
    data = {}

    for X_j in scm.G.nodes:
        if X_j in do_dict:
            continue
        noise_dist = noise_utils.generate_distribution(scm.N[X_j])
        noise_data[X_j] = noise_dist(n_samples)

    for X_j in nx.topological_sort(scm.G):
        if X_j in do_dict:
            intervention = do_dict[X_j]

            if isinstance(intervention, (int, float, str)):
                data[X_j] = np.repeat(float(intervention), n_samples)

            elif isinstance(intervention, dict):
                if "value" in intervention:
                    data[X_j] = np.repeat(float(intervention["value"]), n_samples)
                else:
                    # Evaluate custom function as defined in SCM.F[X_j]
                    f_j = scm.F[X_j]
                    result = _evaluate_function(f_j, data, n_samples)

                    # Optional noise (added if present in scm.N)
                    if X_j in scm.N:
                        noise_dist = noise_utils.generate_distribution(scm.N[X_j])
                        noise = noise_dist(n_samples)
                        result += noise

                    data[X_j] = result

        elif scm.G.in_degree(X_j) == 0:
            data[X_j] = noise_data[X_j]

        else:
            f_j = scm.F[X_j]
            result = _evaluate_function(f_j, data, n_samples)
            data[X_j] = result + noise_data[X_j]

    return data
