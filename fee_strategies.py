import networkx as nx
import copy
import numpy as np
import multiprocessing
import scripts
import psutil

ChCost = 10000
div = 10

max_rew_fee = 1
max_rew = 0
edge_global = -1
global_max_rew = 0
global_rewards = np.zeros(ChCost + 1)
edge_global_rew = np.zeros(ChCost + 1)

print_flag = False

tx_most_freq_fees = {100: 1000.0, 10000: 1010.0, 1000000: 2000.0}
most_freq_fee = -1

"""Function that sets a global variable, to be later used within the code.

:param tx_amt: transaction amount that determines which graph we need to obtain the most common fee value for.
"""
def set_most_freq_fee(tx_amt):
    global tx_most_freq_fees
    global most_freq_fee
    most_freq_fee = tx_most_freq_fees[tx_amt]


"""Function optimizes the edge fees within a given graph.

:param graph: The graph to be optimized.
:returns: The optimized graph.
"""
def graph_fee_optimization(graph):
    calculation_graph = copy.deepcopy(graph)

    available_cores = psutil.cpu_count(logical=False)
    cut_off_amount = 14
    print("Starting graph optimization with %s cores." % available_cores, flush=True)
    if available_cores - 2 <= cut_off_amount:
        cores = available_cores
    else:
        cores = cut_off_amount

    pool = multiprocessing.Pool(cores)

    edge_list = graph.edges(data=True)
    pool_list = []
    new_edges = []

    for edge in edge_list:
        pool_list.append(pool.apply_async(graph_fee_optimization_job, args=(edge, calculation_graph)))
    pool.close()
    pool.join()

    for pool_res in pool_list:
        new_edges.append(pool_res.get())

    for edge in new_edges:
        graph = scripts.add_edge(graph, edge[0], edge[1], edge[2], False)
    return graph


"""Function used for parallelization. It is used to separate the optimization of edge fees into different processes.

:param edge: The edge to be optimized.
:param calculation_graph: The graph to be used during the optimization process.
:returns: A tuple containing the source node, destination node, and the new, more profitable fee. Or nothing if no fee
could be found that is more profitable.
"""
def graph_fee_optimization_job(edge, calculation_graph):
    src_node = edge[0]
    dest_node = edge[1]

    if(print_flag):
        print("Optimizing %s -> %s as part of graph optimization" % (src_node, dest_node), flush=True)
    new_weight = edge_fee_calculation(calculation_graph, edge)
    res = (src_node, dest_node, int(new_weight))
    return res


"""Function optimizes a single edges' fee within a given graph.

:param graph: The graph object.
:param edge: The edge to be optimized.
:returns: The updated graph.
"""
def edge_fee_optimization(graph, edge):
    src_node = edge[0]
    dest_node = edge[1]
    weight = edge[2]['weight']

    max_fee = edge_fee_calculation(graph, edge)

    if weight is not max_fee:
        graph = scripts.add_edge(graph, src_node, dest_node, int(max_fee), False)
        if (print_flag):
            print("Set edge: %s -> %s to fee: %s" % (src_node, dest_node, int(max_fee)), flush=True)
    return graph


"""Function that computes the reward of the source node of edge_global.
It seperates this into the rewards the edge brings, and the reward that all other connected to the source node bring.

:param fee: The fee value to analyse the rewards with.
:param calculation_graph: The graph object used for the computation.
:returns: edge_rew, rest_rew the rewards respectively.
"""
def compute_node_rew_init(fee, calculation_graph):
    edge_rew, rest_rew = compute_node_rew(fee, calculation_graph, edge_global)
    return edge_rew, rest_rew


"""Function that calculates the reward of a target edge.

:param fee: The hypothetical fee to be used for calculation.
:param calculation_graph: The graph snapshot used for the calculation.
:param edge: The edge  to be used during the calculation.
:returns: The optimized graph.
"""
def compute_node_rew(fee, calculation_graph, edge):
    is_only_reroute = True

    local_graph = copy.deepcopy(calculation_graph)
    src_node = edge[0]
    dest_node = edge[1]
    weight = fee

    local_graph = scripts.add_edge(local_graph, src_node, dest_node, weight, False)

    between_cent = nx.edge_betweenness_centrality(local_graph, normalized=False, weight='weight')
    if is_only_reroute:
        src_node = edge[0]
        between_cent = remove_own_betweenness_score(local_graph, src_node, between_cent)

    edge_list = local_graph.out_edges([src_node], data=True)
    edge_rew = 0
    rest_rew = 0
    """
        Calculate the total reward of edge_global's source node.
        This is split into edge_rew which constitutes the reward of edge_global, and rest_rew which represents the 
        rewards of all nodes that share the same source but are not edge_global.
    """
    for edge in edge_list:
        if edge[1] == dest_node:
            edge_rew += weight * between_cent[(src_node, dest_node)]
        else:
            rest_rew += edge[2]['weight'] * between_cent[(src_node, edge[1])]
    return edge_rew, rest_rew


"""Function removes betweenness centrality gained from transactions originating from the source party.

:param graph: The graph to compute the betweenness centrality on.
:param src_id: The source ID of the source within the graph.
:param bet_scores: The previously computed betweenness centrality scores.
:returns: The adjusted betweenness centrality.
"""
def remove_own_betweenness_score(graph, src_id, bet_scores):
    node_ids = graph.nodes()

    for dst in node_ids:
        if src_id != dst:
            paths = nx.all_shortest_paths(graph, src_id, dst, weight='weight')
            path_list = list(paths)
            path_weight = 1 / len(path_list)
            for path in path_list:
                bet_scores[(path[0], path[1])] -= path_weight

    for key in bet_scores.keys():
        value = bet_scores[key]
        if np.abs(value) < 0.0001:
            bet_scores[key] = 0.0
    return bet_scores



"""Function that calculates the optimal fee of an edge within a given graph.
It does so by trying many values within the search space.

:param graph: The graph object.
:param edge: The edge to be optimized.
:returns: The fee that obtained the highest reward.
"""
def edge_fee_calculation(graph, edge):
    global max_rew_fee
    global max_rew
    global edge_global
    global global_max_rew
    global global_rewards
    global edge_global_rew
    global most_freq_fee

    # What is the highest fee that is not from global_edge?
    edge_list = graph.out_edges([edge[0]], data=True)

    highest_fee_found = 0
    for observ_edge in edge_list:
        if observ_edge[1] != edge[1]:
            if observ_edge[2]['weight'] > highest_fee_found:
                highest_fee_found = observ_edge[2]['weight']

    # Create/Update edge in graph to do said fee.
    graph = scripts.add_edge(graph, edge[0], edge[1], highest_fee_found, False)

    # Set max_rew_fee to this value.
    max_rew_fee = highest_fee_found
    global_rewards = np.zeros(ChCost + 1)
    edge_global_rew = np.zeros(ChCost + 1)

    edge_global = edge

    global_max_rew = 0
    max_rew = global_max_rew

    precalculate_fee(graph, highest_fee_found)
    if highest_fee_found < ChCost:
        precalculate_fee(graph, highest_fee_found + 1)
    precalculate_fee(graph, highest_fee_found - 1)

    maximize_channel_reward(graph, 1, ChCost)

    return max_rew_fee


"""Function that precomputes rewards values to reduce the search space.

:param graph: The graph object.
:param fee: The fee the precompute the reward for.
"""
def precalculate_fee(graph, fee):
    global max_rew_fee
    global global_max_rew
    global max_rew

    # Make initial computation just above base value for performance speedup
    local_fee = int(fee)

    e_rew, r_rew = compute_node_rew_init(local_fee, graph)
    global_rewards[local_fee] = e_rew + r_rew
    edge_global_rew[local_fee] = e_rew

    er_local = global_rewards[local_fee]
    if er_local > global_max_rew:
        max_rew_fee = fee
        global_max_rew = er_local
        max_rew = global_max_rew


"""Function that maximizes channel rewards, by efficiently searching different fee values.
By calculating the maximum theoretical reward for an interval, intervals can be discarded aiding in the search.

:param graph: The graph object.
:param min_fee: Lower bound of the search space.
:param max_fee: Upper bound of the search space.
:returns: Void. Return is stored in a global variable.
"""
def maximize_channel_reward(graph, min_fee, max_fee):
    global max_rew_fee
    global max_rew
    global global_max_rew
    global global_rewards
    global edge_global_rew

    er = np.zeros(div + 1)
    er_max = np.zeros(div)

    # If the different fee values present, are less then the amount of divisions.
    # Enter the base
    if max_fee - min_fee <= div:
        # For all the fee candidates, calculate the optimal fee
        for fee in np.arange(min_fee, max_fee + 1):
            if global_rewards[fee] == 0:
                e_rew, r_rew = compute_node_rew_init(fee, graph)
                if e_rew == 0.0:
                    # Therefore in stead of computing them, we'll set them here
                    for index_2 in np.arange(0, div + 1):
                        fee_2 = ((max_fee - min_fee) * index_2 // div) + min_fee
                        if fee_2 > fee:
                            global_rewards[fee_2] = e_rew + r_rew
                            edge_global_rew[fee_2] = e_rew

                global_rewards[fee] = e_rew + r_rew
                edge_global_rew[fee] = e_rew

            er_local = global_rewards[fee]
            # If the calculated fee yields a better reward than the current best, replace it.
            if er_local > global_max_rew:
                max_rew_fee = fee
                global_max_rew = er_local
                max_rew = global_max_rew
        return
    # Else/ Recursion
    else:
        # Separate the fee values into divisions
        for index in np.arange(0, div + 1):
            # Set current div fee
            fee = ((max_fee - min_fee) * index // div) + min_fee
            # Compute fee yield
            if global_rewards[fee] == 0:
                e_rew, r_rew = compute_node_rew_init(fee, graph)

                if e_rew == 0.0: # if e_rew is 0.0, we will obtain the same value for all divs greater then current.
                    # Therefore in stead of computing them, we'll set them here
                    for index_2 in np.arange(0, div + 1):
                        fee_2 = ((max_fee - min_fee) * index_2 // div) + min_fee
                        if fee_2 > fee:
                            global_rewards[fee_2] = e_rew + r_rew
                            edge_global_rew[fee_2] = e_rew

                global_rewards[fee] = e_rew + r_rew
                edge_global_rew[fee] = e_rew

            er[index] = global_rewards[fee]
            # If fee yield is better than current best update
            if er[index] > global_max_rew:
                max_rew_fee = fee
                global_max_rew = er[index]
                max_rew = global_max_rew
            if er[index] == 0:
                break

        # Compute the maximum possible reward for the div
        for index in np.arange(0, div):
            # f_i
            fee = ((max_fee - min_fee) * index // div) + min_fee
            # f_i+1
            fee_next = ((max_fee - min_fee) * (index + 1) // div) + min_fee
            # (r_i * f_i+1) // f_i + (R_i+1 - r_i+1) => (r_i * f_i+1) // f_i + r'_i+1
            er_max[index] = (edge_global_rew[fee] * fee_next) // fee + (er[index + 1] - edge_global_rew[fee_next])

        # Recursively call the interval that contains the highest reward
        for index in np.arange(0, div):
            if er_max[index] > global_max_rew:
                rec_min_fee = ((max_fee - min_fee) * index // div) + min_fee
                rec_max_fee = ((max_fee - min_fee) * (index + 1) // div) + min_fee
                maximize_channel_reward(graph, rec_min_fee, rec_max_fee)
