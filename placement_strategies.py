import networkx as nx
import numpy as np
import scripts
import fee_strategies
import copy
import multiprocessing
import psutil

tx_most_freq_fees = {100: 1000.0, 10000: 1010.0, 1000000: 2000.0}
global_tx_amt = -1

"""Function that sets a global variable, to be later used within the code.

:param tx_amt: the value to be set.
"""
def set_most_freq_fee(tx_amt):
    global global_tx_amt
    global_tx_amt = tx_amt


"""Function that takes as input the list of nodes and a node within a graph and removes the id's that are already 
connected. It returns a list of node id's that are not yet connected, from which then the best connection can be 
calculated.

:param nodelist: List of all the node id's within the graph.
:param edgelist: List of all the edges within the graph.
:param node_id: The node id used to determine if a connection is "new" or already existing.
:returns: The list of node id's that will lead to a new connection.
"""
def remove_connected_nodes(nodelist, edgelist, node_id):
    new_connections = list(nodelist)
    new_connections.remove(node_id)  # One is always connected to oneself
    for edge in edgelist:
        # If we find an edge that contains node_id, we ensure that the other node is not present in new_connections
        if edge[0] == node_id and edge[1] in new_connections:
            new_connections.remove(edge[1])
        elif edge[1] == node_id and edge[0] in new_connections:
            new_connections.remove(edge[0])
    return new_connections


"""Function that adds multiple edges to a graph.

:param graph: The graph object one wishes to add an edge to.
:param choices: List of all destinations for which an edge needs to be created.
:param node_id: The source for the edges that need to be created.
:param src_needs_optimization: Boolean that indicates if the newly created edge needs to have their fee optimized.
:param given_src_fee: Optional parameter that allows one to set the fee of an edge, otherwise a default fee will be used.
:returns: The graph to which edges have been added.
"""
def create_edges(graph, choices, node_id, src_needs_optimization, given_src_fee=None):
    global tx_most_freq_fees
    global global_tx_amt
    default_fee = tx_most_freq_fees[global_tx_amt]

    src_fee = given_src_fee if given_src_fee is not None else default_fee
    dst_fee = default_fee

    for choice in choices:
        graph = scripts.add_edge(graph, node_id, choice, src_fee, src_needs_optimization)
        graph = scripts.add_edge(graph, choice, node_id, dst_fee, False)
    return graph


"""Function for determining how to create new edges connecting a node further to the graph.
The strategy used in this function is uniform random. Here every node that creates a new connection is given the same 
change, and one is selected at random.

:param graph: The graph object one wishes to add an edge to.
:param node_id: The source for the edges that need to be created.
:param n: The number of edges that need to be created using this strategy.
:param src_needs_optimization: Boolean that indicates if the newly created edge needs to have their fee optimized.
:param seed: The seed used to draw a random party ID.
:returns: The graph to which edges have been added.
"""
def uniform_random(graph, node_id, n, needs_optimization, seed=None):
    if seed is not None:
        np.random.seed(seed)

    # Filter nodes already connected with
    node_candidates = remove_connected_nodes(graph.nodes(), graph.edges(data=True), node_id)

    # Pick n node(s) our of the new connection
    if n <= len(node_candidates):
        choices = np.random.choice(node_candidates, n, replace=False)
    else:
        choices = np.random.choice(node_candidates, len(node_candidates), replace=False)

    print("Choice(s):", choices)

    # Add the chosen edges to the network
    graph = create_edges(graph, choices, node_id, needs_optimization)
    return graph


"""Function for determining how to create new edges connecting a node further to the graph.
The strategy used in this function is highest degree. Here the nodes that create a new connection are sorted by how many
existing connections they have. Then the top n nodes are chosen to make this connection with.

:param graph: The graph object one wishes to add an edge to.
:param node_id: The source for the edges that need to be created.
:param n: The number of edges that need to be created using this strategy.
:param src_needs_optimization: Boolean that indicates if the newly created edge needs to have their fee optimized.
:returns: The graph to which edges have been added.
"""
def highest_degree(graph, node_id, n, src_needs_optimization):
    # Sort by degree
    deg_list = sorted(graph.degree(), key=lambda node: node[1], reverse=True)

    # Map sorted degree list to node id's and filter out the nodes already connected
    node_candidates = remove_connected_nodes([tup[0] for tup in deg_list], graph.edges(data=True), node_id)

    # Pick n node(s) our of the new connection
    if n <= len(node_candidates):
        choices = node_candidates[0:n]
    else:
        choices = node_candidates
    # Add the chosen edges to the network
    print("Choice(s): ", choices)
    graph = create_edges(graph, choices, node_id, src_needs_optimization)

    return graph


"""Function for determining how to create new edges connecting a node further to the graph.
The strategy used in this function is betweenness centrality. Here the strategy look at all nodes they are currently not
connected with and simulates the creation of an edge with said node. Upon this simulation it is analyzed how many 
transactions would make use of the new channel if every node were to send a simulated message to every other node, and 
the edge with the highest simulated use will be created within the graph.

:param graph: The graph object one wishes to add an edge to.
:param node_id: The source for the edges that need to be created.
:param n: The number of edges that need to be created using this strategy.
:param src_needs_optimization: Boolean that indicates if the newly created edge needs to have their fee optimized.
:returns: The graph to which edges have been added.
"""
def betweenness_centrality(graph, node_id, n, src_needs_optimization):
    # Record the centrality
    between_cent = nx.betweenness_centrality(graph, normalized=False, weight='weight')
    between_cent_sorted = sorted(between_cent.items(), key=lambda x: x[1], reverse=True)

    # Map sorted degree list to node id's and filter out the nodes already connected
    node_candidates = remove_connected_nodes([tup[0] for tup in between_cent_sorted], graph.edges(data=True), node_id)

    # Pick n node(s) our of the new connection
    if n <= len(node_candidates):
        choices = node_candidates[0:n]
    else:
        choices = node_candidates

    # Add the chosen edges to the network
    print("Choice(s):", choices)
    graph = create_edges(graph, choices, node_id, src_needs_optimization)
    return graph


"""Function for determining how to create new edges connecting a node further to the graph.
The strategy used in this function is k-center. Here the aim is to create new channels to shorten the current longest 
path within the network. It aims to do so from the perspective of "our" source node, the closer we are to every other 
node in the network, the closer every other node in the network is to each other (via us).

:param graph: The graph object one wishes to add an edge to.
:param node_id: The source for the edges that need to be created.
:param n: The number of edges that need to be created using this strategy.
:param src_needs_optimization: Boolean that indicates if the newly created edge needs to have their fee optimized.
:returns: The graph to which edges have been added.
"""
def k_center(graph, node_id, n, src_needs_optimization):
    for i in range(n):
        dist_dict = nx.single_source_dijkstra_path(graph, node_id, weight='weight')
        dist_dict.pop(node_id)

        longest_path_length = -1
        longest_path_destination = -1
        for path in dist_dict.values():
            if len(path) > longest_path_length and len(path) > 2:
                longest_path_length = len(path)
                longest_path_destination = path[-1]

        if longest_path_destination != -1:
            graph = create_edges(graph, [longest_path_destination], node_id, src_needs_optimization)
    return graph


"""Function for determining how to create new edges connecting a node further to the graph.
The strategy used in this function is k-means. Here the aim is to lower the average shortest path within the network.

:param graph: The graph object one wishes to add an edge to.
:param node_id: The source for the edges that need to be created.
:param n: The number of edges that need to be created using this strategy.
:param src_needs_optimization: Boolean that indicates if the newly created edge needs to have their fee optimized.
:returns: The graph to which edges have been added.
"""
def k_means(graph, node_id, n, src_needs_optimization):
    # Init
    node_candidates = remove_connected_nodes(graph.nodes(), graph.edges(data=True), node_id)
    removed_candidates = []
    all_nodes = graph.nodes()

    # Analyze the node candidates until only n remain
    while len(node_candidates) > n:
        min_candid_distance = float('inf')
        min_candid_id = -1

        # Compute which of the candidates is the closest if we take the rest of the graph as source
        for node_candid in node_candidates:
            observation_list = all_nodes - removed_candidates
            observation_list.remove(node_candid)

            res = nx.multi_source_dijkstra_path_length(graph, observation_list, weight='weight')
            candid_dist = res[node_candid]

            # Store minimal distance
            if candid_dist < min_candid_distance and node_candid in node_candidates:
                min_candid_id = node_candid
                min_candid_distance = candid_dist
        # Remove the closest node
        if min_candid_id != -1:
            removed_candidates.append(min_candid_id)
            node_candidates.remove(min_candid_id)
        # Check that should never be reached
        elif min_candid_id == -1:
            break

    # Create the edges to the chosen nodes
    graph = create_edges(graph, node_candidates, node_id, src_needs_optimization)
    return graph


"""Function for determining how to create new edges connecting a node further to the graph.
The strategy used in this function is fee weighted centrality (or greedy). This strategy similar to betweenness 
centrality makes use of the betweenness centrality metric. However this strategy optimizes the weighted fee and edge 
would provide within the simulation, and does not solely rely on the the number of transactions that pass it. 
Note that this method always optimized their fee, therefore there is no src_needs_optimization parameter

:param graph: The graph object one wishes to add an edge to.
:param node_id: The source for the edges that need to be created.
:param n: The number of edges that need to be created using this strategy.
:returns: The graph to which edges have been added.
"""
def fee_weighted_centrality(graph, node_id, n):
    global global_tx_amt
    # Create n new edges
    for i in range(n):
        # Create copy for computation
        calculation_graph = copy.deepcopy(graph)

        # Create new connections list.
        node_candidates = remove_connected_nodes(calculation_graph.nodes(), calculation_graph.edges(data=True), node_id)

        # Init multiprocessing
        available_cores = psutil.cpu_count(logical=False)
        pool = multiprocessing.Pool(available_cores - 2)
        pool_list = []
        edge_candidates = []

        # Try all possible connections in parallel and store
        for node_candid in node_candidates:
            pool_list.append(pool.apply_async(fee_weighted_centrality_job,
                                              args=(calculation_graph, node_id, node_candid, global_tx_amt)))
        pool.close()
        pool.join()

        for pool_res in pool_list:
            edge_candidates.append(pool_res.get())

        # Sort list by reward
        edge_candidates.sort(key=lambda y: y[3], reverse=True)

        # If not empty create the edge that yields the highest reward
        if len(edge_candidates) > 0:
            chosen_candid = edge_candidates[0]
            graph = create_edges(graph, [chosen_candid[1]], chosen_candid[0], False, given_src_fee=chosen_candid[2])
            print("Final choice %s -> %s, fee: %s, reward: %s" % (chosen_candid[0], chosen_candid[1], chosen_candid[2], chosen_candid[3]))

    return graph


"""Function to optimize the fee of one edge. This job is used as part of fee_weighted_centrality to allow for multiprocessing.

:param calculation_graph: A snapshot of the graph object for analysis.
:param node_id: The source for the edges that need to be created.
:param node_candid: The candidate destination ID.
:param global_tx: Parameter to set the default fee (global fee indicates what the the amount is of the simulated transaction in the graph)
:returns: The graph to which edges have been added.
"""
def fee_weighted_centrality_job(graph, node_id, node_candid, global_tx):
    global tx_most_freq_fees
    default_fee = tx_most_freq_fees[global_tx]

    calculation_graph = copy.deepcopy(graph)

    # Create the candidate edge
    calculation_graph = scripts.add_edge(calculation_graph, node_id, node_candid, default_fee, True)
    calculation_graph = scripts.add_edge(calculation_graph, node_candid, node_id, default_fee, False)

    edge = scripts.get_edge(calculation_graph, node_id, node_candid)
    fee = edge[2]['weight']
    edge_rew, rest_rew = fee_strategies.compute_node_rew(fee, calculation_graph, edge)
    reward = edge_rew + rest_rew

    # Remove the candidate edge
    calculation_graph = scripts.remove_edge(calculation_graph, node_id, node_candid)

    res = (node_id, node_candid, fee, reward)
    return res


"""Function for determining how to create new edges connecting a node further to the graph.
The strategy used in this function is based on the anticipated reaction of the network. Calculating the expected reward 
based on the network reaction allows one to pick the connection that retains the highest reward after the network has 
reacted.

:param graph: The graph object one wishes to add an edge to.
:param node_id: The source for the edges that need to be created.
:param n: The number of edges that need to be created using this strategy.
:param scenario_dict: scenario_dict is used to determine which analysis to perform. It it meant to have only key that 
determines the scenario, with the value being the parameter for said scenario.
:returns: The graph to which edges have been added.
"""
def game_theory(graph, node_id, n, scenario_dict):
    global global_tx_amt
    # Create n new edges
    for i in range(n):
        # Create copy for computation
        calculation_graph = copy.deepcopy(graph)

        # Create new connections list.
        node_candidates = remove_connected_nodes(calculation_graph.nodes(), calculation_graph.edges(data=True), node_id)

        # Init multiprocessing
        available_cores = psutil.cpu_count(logical=False)
        pool = multiprocessing.Pool(available_cores - 2)
        pool_list = []
        edge_candidates = []

        # Try all possible connections in parallel and store
        for node_candid in node_candidates:
            pool_list.append(pool.apply_async(fee_weighted_centrality_job,
                                              args=(calculation_graph, node_id, node_candid, global_tx_amt)))

        # Wait for the spawned processes to finish
        pool.close()
        pool.join()

        # Unpack the value from the processes
        for pool_res in pool_list:
            edge_candidates.append(pool_res.get())

        # Close the pool, to allow new jobs to be assigned to the pool object
        pool.terminate()

        # Sort list by reward
        edge_candidates.sort(key=lambda y: y[3], reverse=True)

        # Init multiprocessing
        game_theory_edge_candidates = []

        scenario_dict_keys = scenario_dict.keys()
        # Multiprocessing based on the scenario_flag
        if "network" in scenario_dict_keys:
            for gt_candid in edge_candidates:
                game_theory_edge_candidates.append(game_theory_network_job(calculation_graph, gt_candid[0], gt_candid[1], gt_candid[2], gt_candid[3]))
        elif "party" in scenario_dict_keys:
            for gt_candid in edge_candidates:
                scenario_params = scenario_dict["party"]
                game_theory_edge_candidates.append(game_theory_party_job(calculation_graph, gt_candid[0], gt_candid[1], gt_candid[2], gt_candid[3], scenario_params))

        # Wait for the spawned processes to finish
        pool.close()
        pool.join()

        # Close the pool, to allow new jobs to be assigned to the pool object
        pool.terminate()

        # Sort list by reward
        game_theory_edge_candidates.sort(key=lambda y: y[5], reverse=True)

        # If not empty create the edge that yields the highest reward
        if len(game_theory_edge_candidates) > 0:
            chosen_candid = game_theory_edge_candidates[0]
            graph = create_edges(graph, [chosen_candid[1]], chosen_candid[0], False, given_src_fee=chosen_candid[2])
            print("Final Game Theory choice ID:", chosen_candid[1], flush=True)
            return graph, chosen_candid
    return graph, None


"""Function to analyse the case that the network will react to the result of our game theoretical choice.

:param graph: The graph object for analysis.
:param source: Source ID.
:param dest: Destination ID.
:param fee: The fee to be analysed.
:param initial_reward: The initial rewards when using fee=fee
:returns: Object containing the resulting hypothetical reward.
"""
def game_theory_network_job(graph, source, dest, fee, initial_reward):
    calculation_graph = copy.deepcopy(graph)

    # Create the candidate edge
    calculation_graph = create_edges(calculation_graph, [dest], source, False, given_src_fee=fee)

    # Update network fees
    calculation_graph = fee_strategies.graph_fee_optimization(calculation_graph)

    # Get the edge object for our analysis
    observing_edge = scripts.get_edge(calculation_graph, source, dest)
    new_fee = observing_edge[2]['weight']

    # Compute the reward that our observing edge brings in after the network update
    edge_rew, rest_rew = fee_strategies.compute_node_rew(new_fee, calculation_graph, observing_edge)
    reward = edge_rew + rest_rew

    # Remove the candidate edge
    calculation_graph = scripts.remove_edge(calculation_graph, source, dest)

    res = (source, dest, fee, initial_reward, new_fee, reward)
    return res


"""Function to analyse the case that the other parties will react to the result of our game theoretical choice.

:param graph: The graph object for analysis.
:param source: Source ID.
:param dest: Destination ID.
:param fee: The fee to be analysed.
:param initial_reward: The initial rewards when using fee=fee
:param scenario_params: Dict for extra information (in this case we use it to pass the ID's of 'other parties')
:returns: Object containing the resulting hypothetical reward.
"""
def game_theory_party_job(graph, source, dest, fee, initial_reward, scenario_params):
    calculation_graph = copy.deepcopy(graph)

    # Create the candidate edge
    calculation_graph = create_edges(calculation_graph, [dest], source, False, given_src_fee=fee)

    # Other party adds their edge
    other_node_id = scenario_params[0]
    calculation_graph = fee_weighted_centrality(calculation_graph, other_node_id, 1)

    # Get the edge object for our analysis
    observing_edge = scripts.get_edge(calculation_graph, source, dest)
    new_fee = observing_edge[2]['weight']

    # Compute the reward that our observing edge brings in after the network update
    edge_rew, rest_rew = fee_strategies.compute_node_rew(new_fee, calculation_graph, observing_edge)
    reward = edge_rew + rest_rew

    # Remove the candidate edge
    calculation_graph = scripts.remove_edge(calculation_graph, source, dest)

    res = (source, dest, fee, initial_reward, new_fee, reward)
    return res
