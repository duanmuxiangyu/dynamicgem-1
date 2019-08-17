import numpy as np
import pdb

precision_pos = [2, 10, 100, 200, 300, 500, 1000]


def computePrecisionCurve(predicted_edge_list, true_digraph, max_k=-1):
    """Function to calculate the precision curve
           
           Attributes:
               predicted_edge_list (list): List of predicted edges.
               true_digraph (object): original graph
               max_k(int): precision@k

            Returns:
                ndarray: precision_scores, delta_factors
    """
    if max_k == -1:
        max_k = len(predicted_edge_list)
    else:
        max_k = min(max_k, len(predicted_edge_list))

    sorted_edges = sorted(predicted_edge_list, key=lambda x: x[2], reverse=True)

    precision_scores = []
    delta_factors = []
    correct_edge = 0
    for i in range(max_k):
        if true_digraph.has_edge(sorted_edges[i][0], sorted_edges[i][1]):
            correct_edge += 1
            delta_factors.append(1.0)
        else:
            delta_factors.append(0.0)
        precision_scores.append(1.0 * correct_edge / (i + 1))
    return precision_scores, delta_factors


def computeMAP(predicted_edge_list, true_digraph, max_k=-1):
    """Function to calculate Mean Average Precision
           
           Attributes:
               predicted_edge_list (list): List of predicted edges.
               true_digraph (object): original graph
               max_k(int): precision@k

            Returns:
                Float: Mean Average Precision score
    """
    node_num = true_digraph.number_of_nodes()
    node_edges = []
    for i in range(node_num):
        node_edges.append([])
    for (st, ed, w) in predicted_edge_list:
        node_edges[st].append((st, ed, w))
    node_AP = [0.0] * node_num
    count = 0
    for i in range(node_num):
        if true_digraph.out_degree(i) == 0:
            continue
        count += 1
        precision_scores, delta_factors = computePrecisionCurve(node_edges[i], true_digraph, max_k)
        precision_rectified = [p * d for p, d in zip(precision_scores, delta_factors)]
        if (sum(delta_factors) == 0):
            node_AP[i] = 0
        else:
            node_AP[i] = float(sum(precision_rectified) / sum(delta_factors))
    return sum(node_AP) / count


def checkedges(edge_list, e):
    """Function to check if the given edgelist matches.
           
           Attributes:
               edge_list (list): List of predicted edges.
               e (list): Original edge list

            Returns:
                bool: Boolean result to denoe if all the edges matches.
    """
    val = False

    for k in edge_list:
        if type(e) is tuple:
            if k[1] == e[1] and k[0] == e[0]:
                val = True
        else:
            for ee in e:
                if k[1] == ee[1] and k[0] == ee[0]:
                    val = True

    return val


def getMetricsHeader():
    """Function to get the header for storing the result"""
    header = 'MAP\t' + '\t'.join(['P@%d' % p for p in precision_pos])
    header = header + '\tP@EdgeNum'
    return header


def getPrecisionReport(prec_curv, edge_num):
    """Function to get the report summary for precision"""
    result_str = ''
    temp_pos = precision_pos[:] + [edge_num]
    for p in temp_pos:
        if (p < len(prec_curv)):
            result_str += '\t%f' % prec_curv[p - 1]
        else:
            result_str += '\t-'
    return result_str[1:]


# We define StabilityDeviation of nxd embeddings X1 and X2,
# nxn adjacenecy matrices S1 and S2 as:
# StabDev = (||S1||_F * ||X2 - X1||_F) / (||X1||_F * ||S2 - S1||_F)
def getStabilityDev(X1, X2, S1, S2):
    """Function to get the deviation froms stability"""
    n1, d = X1.shape
    return (np.linalg.norm(S1) * np.linalg.norm(X2[:n1, :] - X1)) / (
                np.linalg.norm(X1) * np.linalg.norm(S2[:n1, :n1] - S1))


def getEmbeddingShift(X1, X2, S1, S2):
    """Function to get the shift in embedding"""
    n1, d = X1.shape
    return (np.linalg.norm(X2[:n1, :] - X1)) / (n1 * d)


def getNodeAnomaly(X_dyn):
    """Function to get the node anomaly"""
    T = len(X_dyn)
    n_nodes = X_dyn[0].shape[0]
    node_anom = np.zeros((n_nodes, T - 1))
    for t in range(T - 1):
        node_anom[:, t] = np.linalg.norm(X_dyn[t + 1][:n_nodes, :] - X_dyn[t][:n_nodes, :], axis=1)
    return node_anom


def computePrecisionCurve_changed(predicted_edge_list, true_digraph, node_edges_rm, max_k=-1):
    """Function to calculate Preicison curve of changed graph
           
           Attributes:
               predicted_edge_list (list): List of predicted edges.
               true_digraph (object): original graph
               node_edges_rm (list): list of edges removed from the original graph.
               max_k(int): precision@k

            Returns:
                Float: Mean Average Precision score
    """
    if max_k == -1:
        max_k = len(predicted_edge_list) + len(node_edges_rm)
    else:
        max_k = min(max_k, len(predicted_edge_list) + len(node_edges_rm))

    sorted_edges = sorted(predicted_edge_list, key=lambda x: x[2], reverse=True)

    precision_scores = []
    delta_factors = []
    correct_edge = 0
    for i in range(len(predicted_edge_list)):
        if true_digraph.has_edge(sorted_edges[i][0], sorted_edges[i][1]):
            correct_edge += 1
            delta_factors.append(1.0)
        else:
            delta_factors.append(0.0)
        precision_scores.append(1.0 * correct_edge / (i + 1))

    # pdb.set_trace()
    if node_edges_rm:
        for j in range(len(node_edges_rm)):
            if not checkedges(predicted_edge_list, node_edges_rm[j]):
                correct_edge += 1
                delta_factors.append(1.0)
            else:
                delta_factors.append(0.0)
            precision_scores.append(1.0 * correct_edge / (len(predicted_edge_list) + j + 1))

        # pdb.set_trace()
    return precision_scores, delta_factors


def computeMAP_changed(predicted_edge_list, true_digraph, node_dict, edges_rm, max_k=-1):
    """Function to calculate MAP of the change graph
           
           Attributes:
               predicted_edge_list (list): List of predicted edges.
               true_digraph (object): original graph
               node_dict (dict): Dictionary for the nodes.
               node_edges_rm (list): list of edges removed from the original graph.
               max_k(int): precision@k

            Returns:
                Float: Mean Average Precision score
    """
    node_num = true_digraph.number_of_nodes()
    node_edges = []
    for i in range(node_num):
        node_edges.append([])
    for (st, ed, w) in predicted_edge_list:
        node_edges[st].append((st, ed, w))

    node_edges_rm = []
    for i in range(node_num):
        node_edges_rm.append([])
    for st, ed in edges_rm[0]:
        node_edges_rm[node_dict[st]].append((node_dict[st], node_dict[ed], 1))

        # pdb.set_trace()
    node_AP = [0.0] * node_num
    count = 0
    for i in range(node_num):
        if true_digraph.out_degree(i) == 0:
            continue
        count += 1
        precision_scores, delta_factors = computePrecisionCurve_changed(node_edges[i], true_digraph, node_edges_rm[i],
                                                                        max_k)
        precision_rectified = [p * d for p, d in zip(precision_scores, delta_factors)]
        if (sum(delta_factors) == 0):
            node_AP[i] = 0
        else:
            node_AP[i] = float(sum(precision_rectified) / sum(delta_factors))
    return sum(node_AP) / count
