"""Graph Skeleton Recovery models base class.

Author: Diviyan Kalainathan
Date : 7/06/2017
"""
import networkx as nx
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from ...utils.Settings import SETTINGS


class GraphSkeletonModel(object):
    """Base class for undirected graph recovery directly out of data."""

    def __init__(self):
        """Init the model."""
        super(GraphSkeletonModel, self).__init__()

    def predict(self, data):
        """Infer a undirected graph out of data.

        Args:
            data (pandas.DataFrame): observational data

        Returns:
            networkx.Graph: Graph skeleton

        .. warning::
           Not implemented. Implemented by the algorithms.
        """
        raise NotImplementedError


class FeatureSelectionModel(GraphSkeletonModel):
    """Base class for methods using feature selection
    on each variable independently.
    """

    def __init__(self):
        """Init the model."""
        super(FeatureSelectionModel, self).__init__()

    def predict_features(self, df_features, df_target, idx=0, **kwargs):
        """For one variable, predict its neighbouring nodes.

        Args:
            df_features (pandas.DataFrame):
            df_target (pandas.Series):
            idx (int): (optional) for printing purposes
            kwargs (dict): additional options for algorithms

        Returns:
            list: scores of each feature relatively to the target

        .. warning::
           Not implemented. Implemented by the algorithms.
        """
        raise NotImplementedError

    def run_feature_selection(self, df_data, target, idx=0, **kwargs):
        """Run feature selection for one node: wrapper around
        ``self.predict_features``.

        Args:
            df_data (pandas.DataFrame): All the observational data
            target (str): Name of the target variable
            idx (int): (optional) For printing purposes

        Returns:
            list: scores of each feature relatively to the target
        """
        list_features = list(df_data.columns.values)
        list_features.remove(target)
        df_target = pd.DataFrame(df_data[target], columns=[target])
        df_features = df_data[list_features]

        return self.predict_features(df_features, df_target, idx=idx, **kwargs)

    def predict(self, df_data, threshold=0.05, **kwargs):
        """Predict the skeleton of the graph from raw data.

        Returns iteratively the feature selection algorithm on each node.

        Args:
            df_data (pandas.DataFrame): data to construct a graph from
            threshold (float): cutoff value for feature selection scores
            kwargs (dict): additional arguments for algorithms

        Returns:
            networkx.Graph: predicted skeleton of the graph.
        """
        nb_jobs = kwargs.get("nb_jobs", SETTINGS.NB_JOBS)
        list_nodes = list(df_data.columns.values)
        if nb_jobs != 1:
            result_feature_selection = Parallel(n_jobs=nb_jobs)(delayed(self.run_feature_selection)
                                                                (df_data, node, idx, **kwargs)
                                                                for idx, node in enumerate(list_nodes))
        else:
            result_feature_selection = [self.run_feature_selection(df_data, node, idx, **kwargs) for idx, node in enumerate(list_nodes)]
        for idx, i in enumerate(result_feature_selection):
            try:
                i.insert(idx, 0)
            except AttributeError:  # if results are numpy arrays
                result_feature_selection[idx] = np.insert(i, idx, 0)
        matrix_results = np.array(result_feature_selection)
        matrix_results *= matrix_results.transpose()
        np.fill_diagonal(matrix_results, 0)
        matrix_results /= 2

        graph = nx.Graph()

        for (i, j), x in np.ndenumerate(matrix_results):
            if matrix_results[i, j] > threshold:
                graph.add_edge(list_nodes[i], list_nodes[j],
                               weight=matrix_results[i, j])
        for node in list_nodes:
            if node not in graph.nodes():
                graph.add_node(node)
        return graph

