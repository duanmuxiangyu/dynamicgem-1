#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

from dynamicgem.embedding.dynamic_graph_embedding import DynamicGraphEmbedding
from dynamicgem.utils import graph_util
from dynamicgem.utils import plot_util
from dynamicgem.visualization import plot_dynamic_sbm_embedding
from dynamicgem.graph_generation import dynamic_SBM_graph


class GraphFactorization(DynamicGraphEmbedding):
    """Graph Facgorization based network embedding
    
    It utilizes factorization based method to acquire the 
    embedding of the graph nodes.

    Args:
        d (int): dimension of the embedding
        eta (float): learning rate of sgd
        regu (float): regularization coefficient of magnitude of weights
        beta (float): penalty parameter in matrix B of 2nd order objective
        n_iter (int): number of sgd iterations for first embedding (const)
        method_name (str): method name
        initEmbed (Matrix):  Previous timestep embedding initialized for the current timestep

    Examples:
        >>> from dynamicgem.embedding.graphFac_dynamic import GraphFactorization
        >>> from dynamicgem.graph_generation import dynamic_SBM_graph
        >>> node_num = 100
        >>> community_num = 2
        >>> node_change_num = 2
        >>> length = 5
        >>> dynamic_sbm_series = dynamic_SBM_graph.get_random_perturbation_series_v2(node_num, community_num, length,
                                                                              node_change_num)
        >>> dynamic_embeddings = GraphFactorization(100, 100, 10, 5 * 10 ** -2, 1.0, 1.0)
        >>> dynamic_embeddings.learn_embeddings([g[0] for g in dynamic_sbm_series])

        >>> plot_dynamic_sbm_embedding.plot_dynamic_sbm_embedding(dynamic_embeddings.get_embeddings(), dynamic_sbm_series)
        >>> plt.show()
    """

    def __init__(self, d, n_iter, n_iter_sub, eta, regu, kappa, initEmbed=None):
        """ Initialize the GraphFactorization class"""

        self._d = d
        self._eta = eta
        self._regu = regu
        self._n_iter = n_iter
        self._n_iter_sub = n_iter_sub
        self._kappa = kappa
        self._method_name = 'graph_factor_sgd'
        if initEmbed is not None:
            self._initEmbed = initEmbed

    def get_method_name(self):
        """Function to return the method name.
            
           Returns:
                String: Name of the method.
        """
        return self._method_name

    def get_method_summary(self):
        """Function to return the summary of the algorithm. 
           
           Returns:
                String: Method summary
        """
        return '%s_%d' % (self._method_name, self._d)

    def getFVal(self, adj_mtx, X, prev_step_emb=None):
        """Function to Factorize the adjacency matrix."""
        f1 = np.linalg.norm(adj_mtx - np.dot(X, X.T)) ** 2
        f2 = self._regu * (np.linalg.norm(X) ** 2)
        f3 = 0
        if prev_step_emb is not None:
            f3 = self._kappa * (
                    np.linalg.norm(X[:prev_step_emb.shape[0], :prev_step_emb.shape[1]] - prev_step_emb) ** 2)
        # print 'Prev[0][0]: %g, curr[0][0]: %g' % (prev_step_emb[0][0], X[0][0])
        return [f1, f2, f3, f1 + f2 + f3]

    def learn_embedding(self, graph, prevEmbed=None):
        """Learns the embedding of the nodes.
           
           Attributes:
               graph (Object): Networkx Graph Object

            Returns:
                List: Node embeddings and time taken by the algorithm
        """
        # pdb.set_trace()
        A = graph_util.transform_DiGraph_to_adj(graph)
        if not np.allclose(A.T, A):
            print("laplace eigmap approach only works for symmetric graphs!")
            return

        self._node_num = A.shape[0]
        edgeList = np.where(A > 0)
        self._num_iter = self._n_iter
        self._X = 0.01 * np.random.randn(self._node_num, self._d)
        if prevEmbed is not None:
            print('Initializing X_t with X_t-1')
            # self._X = 0.01*np.random.randn(self._node_num, self._d)
            self._X[:prevEmbed.shape[0], :] = np.copy(prevEmbed)
            self._num_iter = self._n_iter_sub
        # pdb.set_trace()

        for iter_id in range(self._num_iter):
            if not iter_id % 100:
                [f1, f2, f3, f] = self.getFVal(A, self._X, prevEmbed)
                print('Iter: %d, Objective value: %g, f1: %g, f2: %g, f3: %g' % (iter_id, f, f1, f2, f3))

            for i, j in zip(edgeList[0], edgeList[1]):
                if i >= j:
                    continue
                delPhi1 = -(A[i, j] - np.dot(self._X[i, :], self._X[j, :])) * self._X[j, :]
                delPhi2 = self._regu * self._X[i, :]
                delPhi3 = np.zeros(self._d)
                if prevEmbed is not None and i < prevEmbed.shape[0]:
                    delPhi3 = self._kappa * (self._X[i, :] - prevEmbed[i, :])
                delPhi = delPhi1 + delPhi2 + delPhi3
                self._X[i, :] -= self._eta * delPhi
            # if prevEmbed is not None:
            # 	print '(i, j) = (%d, %d)' % (i, j)

            if not iter_id % 100:
                print('Iter: %d, Del values: %g, del_f1: %g, del_f2: %g, del_f3: %g' % (
                    iter_id, delPhi[0], delPhi1[0], delPhi2[0], delPhi3[0]))

        return self._X

    def learn_embeddings(self, graphs, prevStepInfo=False):
        """Learning the graph embedding from the adjcency matrix.
		Args:
			graphs: the graphs to embed in networkx DiGraph format
		"""
        self._kappas = self._kappa
        if prevStepInfo:
            self._Xs = [np.copy(self.learn_embedding(graphs[0], self._initEmbed))]
        else:
            self._Xs = [np.copy(self.learn_embedding(graphs[0]))]
        for i in range(1, len(graphs)):
            # pdb.set_trace()
            X_curr = graph_util.transform_DiGraph_to_adj(graphs[i])
            X_prev = graph_util.transform_DiGraph_to_adj(graphs[i - 1])
            delX = abs(X_curr - X_prev)
            beta = 0.01
            M_g = np.eye(X_curr.shape[0]) - beta * delX
            M_l = beta * delX  # np.dot(delX, delX)#
            S = np.dot(np.linalg.inv(M_g), M_l)
            S_sum = np.sum(S, 1)
            S_sum[S_sum == 0] = 0.01
            self._kappas = self._kappa / S_sum
            self._eta /= 10
            self._Xs.append(np.copy(self.learn_embedding(graphs[i], self._Xs[i - 1])))

        return self._Xs

    def get_embedding(self):
        """Function to return a single  graph embedding"""
        return self._X

    def get_embeddings(self):
        """Function to return the whole tempral graphs embeddings"""
        return self._Xs

    def get_edge_weight(self, i, j):
        """Function to get edge weight.
           
            Attributes:
              i (int): source node for the edge.
              j (int): target node for the edge.
              embed (Matrix): Embedding values of all the nodes.
              filesuffix (str): File suffix to be used to load the embedding.

            Returns:
                Float: Weight of the given edge.
        """
        return np.dot(self._X[i, :], self._X[j, :])

    def get_reconstructed_adj(self, X=None):
        """Function to reconstruct the adjacency list for the given node.
           
            Attributes:
              node_l (int): node for which the adjacency list will be created.
              embed (Matrix): Embedding values of all the nodes.
              filesuffix (str): File suffix to be used to load the embedding.

            Returns:
                List : Adjacency list of the given node.
        """
        if X is not None:
            self._X = X
            self._node_num = X.shape[0]
        adj_mtx_r = np.zeros((self._node_num, self._node_num))  # G_r is the reconstructed graph
        for v_i in range(self._node_num):
            for v_j in range(self._node_num):
                if v_i == v_j:
                    continue
                adj_mtx_r[v_i, v_j] = self.get_edge_weight(v_i, v_j)
        return adj_mtx_r
