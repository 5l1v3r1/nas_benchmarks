import os
import numpy as np
import ConfigSpace

from nasbench.lib import graph_util
from nasbench import api

MAX_EDGES = 9
VERTICES = 7


class NASCifar10(object):

    def __init__(self, data_dir):

        self.dataset = api.NASBench(os.path.join(data_dir, 'nasbench_full.tfrecord'))
        self.X = []
        self.y_valid = []
        self.y_test = []
        self.costs = []

        self.y_star_valid = 0.04944576819737756  # lowest mean validation error
        self.y_star_test = 0.056824247042338016  # lowest mean test error

    @staticmethod
    def objective_function(self, config):
        pass

    def record_invalid(self, config, valid, test, costs):
        self.X.append(config)
        self.y_valid.append(valid)
        self.y_test.append(test)
        self.costs.append(costs)

    def record_valid(self, config, model_spec, budget):
        self.X.append(config)
        data = self.dataset.get_model_metrics(model_spec)

        # compute mean test error for the final budget
        mean_test_error = 1 - np.mean([data[108][i]["test_accuracy"][1] for i in range(3)])
        self.y_test.append(mean_test_error)

        # compute mean validation error for the chosen budget
        mean_valid_error = 1 - np.mean([data[budget][i]["validation_accuracy"][1] for i in range(3)])
        self.y_valid.append(mean_valid_error)

        mean_runtime = np.mean([data[budget][i]["training_time"][1] for i in range(3)])
        self.costs.append(mean_runtime)

    @staticmethod
    def get_configuration_space():
        pass

    def get_results(self, ignore_invalid_configs=False):

        regret_validation = []
        regret_test = []
        runtime = []
        rt = 0

        inc_valid = np.inf
        inc_test = np.inf

        for i in range(len(self.X)):

            if ignore_invalid_configs and self.costs[i] == 0:
                continue

            if inc_valid > self.y_valid[i]:
                inc_valid = self.y_valid[i]
                inc_test = self.y_test[i]

            regret_validation.append(float(inc_valid - self.y_star_valid))
            regret_test.append(float(inc_test - self.y_star_test))
            rt += self.costs[i]
            runtime.append(float(rt))

        res = dict()
        res['regret_validation'] = regret_validation
        res['regret_test'] = regret_test
        res['runtime'] = runtime

        return res


class NASCifar10A(NASCifar10):
    def objective_function(self, config, budget=108):
        # bit = 0
        # for i in range(VERTICES * (VERTICES - 1) // 2):
        #     bit += config["edge_%d" % i] * 2 ** i
        # matrix = np.fromfunction(graph_util.gen_is_edge_fn(bit),
        #                          (VERTICES, VERTICES),
        #                          dtype=np.int8)
        matrix = np.zeros([VERTICES, VERTICES], dtype=np.int8)
        idx = np.triu_indices(matrix.shape[0], k=1)
        for i in range(VERTICES * (VERTICES - 1) // 2):
            row = idx[0][i]
            col = idx[1][i]
            matrix[row, col] = config["edge_%d" % i]

        if not graph_util.is_full_dag(matrix) or graph_util.num_edges(matrix) > MAX_EDGES:
            self.record_invalid(config, 1, 1, 0)
            return 1, 0

        labeling = [config["op_node_%d" % i] for i in range(5)]
        labeling = ['input'] + list(labeling) + ['output']
        model_spec = api.ModelSpec(matrix, labeling)
        data = self.dataset.query(model_spec, num_epochs=budget)
        self.record_valid(config, model_spec, budget)

        return 1 - data["validation_accuracy"], data["training_time"]

    @staticmethod
    def get_configuration_space():
        cs = ConfigSpace.ConfigurationSpace()

        ops_choices = ['conv1x1-bn-relu', 'conv3x3-bn-relu', 'maxpool3x3']
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_0", ops_choices))
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_1", ops_choices))
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_2", ops_choices))
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_3", ops_choices))
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_4", ops_choices))
        for i in range(VERTICES * (VERTICES - 1) // 2):
            cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("edge_%d" % i, [0, 1]))
        return cs


class NASCifar10B(NASCifar10):
    def objective_function(self, config, budget=108):

        bitlist = [0] * (VERTICES * (VERTICES - 1) // 2)
        for i in range(MAX_EDGES):
            bitlist[config["edge_%d" % i]] = 1
        out = 0
        for bit in bitlist:
            out = (out << 1) | bit

        matrix = np.fromfunction(graph_util.gen_is_edge_fn(out),
                                 (VERTICES, VERTICES),
                                 dtype=np.int8)
        if not graph_util.is_full_dag(matrix) or graph_util.num_edges(matrix) > MAX_EDGES:
            self.record_invalid(config, 1, 1, 0)
            return 1, 0

        labeling = [config["op_node_%d" % i] for i in range(5)]
        labeling = ['input'] + list(labeling) + ['output']
        model_spec = api.ModelSpec(matrix, labeling)
        data = self.dataset.query(model_spec, num_epochs=budget)
        self.record_valid(config, model_spec, budget)

        return 1 - data["validation_accuracy"], data["training_time"]

    @staticmethod
    def get_configuration_space():
        cs = ConfigSpace.ConfigurationSpace()

        ops_choices = ['conv1x1-bn-relu', 'conv3x3-bn-relu', 'maxpool3x3']
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_0", ops_choices))
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_1", ops_choices))
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_2", ops_choices))
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_3", ops_choices))
        cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("op_node_4", ops_choices))
        cat = [i for i in range((VERTICES * (VERTICES - 1)) // 2)]
        for i in range(MAX_EDGES):
            cs.add_hyperparameter(ConfigSpace.CategoricalHyperparameter("edge_%d" % i, cat))
        return cs
