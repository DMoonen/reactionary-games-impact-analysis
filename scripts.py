import networkx as nx
import json
import matplotlib.pyplot as plt
import fee_strategies
import placement_strategies
import numpy as np

"""Function that load the data from json from filepath.

:param filepath: The filepath from the root directory one wishes to load the json from.
:returns: The data object present in the json file.
"""
def read_json(file_path):
    with open(file_path, encoding="utf8") as file:
        data = json.load(file)
    file.close()
    return data


"""Function that writes the data to a json file in storage.

:param data: The data object one wishes to write to storage.
:param filepath: The filepath from the root directory one wishes to write the data to.
:returns: void.
"""
def write_json(data, file_path):
    fl = open(file_path, "w")
    json.dump(data, fl)
    fl.close()


"""Function that searches the edge object from a graph object.

:param graph: The graph to search.
:param src_nodes: The node_id (char) of the source.
:param dest_nodes: The node_id (char) of the destination.
:param is_data: Boolean specifying whether the attribute dictionary contained within the edge should be returned.
:returns: Returns the edge if found, -1 otherwise.
"""
def get_edge(graph, src_node, dest_node):
    try:
        edge_list = graph.out_edges([src_node], data=True)
        for search_candid in edge_list:
            if dest_node == search_candid[1]:
                return search_candid
        return -1
    except:
        print("When attempting to obtain the edge %s -> %s, the search returned an error" % (src_node, dest_node))


"""Function that adds an edge to a given graph.
:param graph: The graph object one wishes to add an edge to.
:param node1: The source of the edge.
:param node2: The destination of the edge.
:param weight: The weight associated to the edge to be created.
:param needs_optimization: 
:returns: The graph to which an edge has been added.
"""
def add_edge(graph, node1, node2, weight, needs_optimization):
    graph.add_edge(node1, node2, weight=weight)
    if needs_optimization:
        edge = get_edge(graph, node1, node2)
        graph = fee_strategies.edge_fee_optimization(graph, edge)
    return graph


"""Function that removes an edge from a given graph.

:param graph: The graph object one wishes to remove an edge from.
:param node1: The source of the edge to be removed.
:param node2: The destination of the edge to be removed.
:returns: The graph from which an edge has been removed.
"""
def remove_edge(graph, node1, node2):
    graph.remove_edge(node1, node2)
    graph.remove_edge(node2, node1)
    return graph


"""Function that adds a node to a given graph.

:param graph: The graph object one wishes to add a node to.
:returns: The graph to which a node has been added.
"""
def add_node(graph):
    new_node_id = str(int(list(graph.nodes())[-1]) + 1)
    graph.add_node(new_node_id)
    return graph, new_node_id


"""Function that initializes a dictionary that keeps track of the reward each nodes has obtained.
The keys are the nodes, with the value being a list of rewards to keep track of rewards over time.

:param graph: The graph object one wishes to create a reward dictionary for.
:returns: The initialized reward dictionary.
"""
def init_reward_list(graph):
    rewards = {}
    for node in graph.nodes():
        rewards[node] = []
    return rewards


"""Function that calculated the reward obtained by each node in a graph at a given time.
Every node within the network sends a simulated message to each other node. 
The fees of these messages are aggregated by source node for each of the edges, and then stored as the hypothetical 
reward that corresponds to the given graph.

:param graph: The graph object one wishes to calculate the rewards over.
:param prev_rewards: The reward dictionary one wishes to add the rewards to.
:returns: The updated reward dictionary.
"""
def calc_node_profit(graph, prev_rewards):
    is_only_reroute = True

    for node in graph.nodes():
        prev_rewards[node].append(0)

    between_cent = nx.edge_betweenness_centrality(graph, normalized=False, weight='weight')
    if is_only_reroute:
        for node in list(graph.nodes()):
            src_node = node
            between_cent = fee_strategies.remove_own_betweenness_score(graph, src_node, between_cent)
    for edge in graph.edges(data=True):
        weight = edge[2]['weight']
        freq_key = (edge[0], edge[1])
        prev_rewards[edge[0]][-1] += between_cent[freq_key] * weight

    return prev_rewards


"""Function creates a plot of the node id's that are present in the node_list.

:param rewards: The reward dictionary.
:param node_list: The list of nodes of which one want the corresponding rewards plotted.
:returns: Void.
"""
def plot_rewards_graph(save_path, rewards, node_list, marker_list=['o'], given_color='b', labels=None):
    #  xaxis is interval [1, #iterations]
    xaxis = range(1, len(rewards[list(node_list)[0]]) + 1)
    for i in range(len(node_list)):
        node = node_list[i]
        label="Node %s" % node
        if labels is not None:
            label = labels[i]
        plt.plot(xaxis, rewards[node], label=label, marker=marker_list[0], color=given_color)
    plt.xticks(xaxis)
    plt.xlabel('Time (# Iteration)')
    plt.ylabel('Reward (#Milli Satoshi\'s)')
    plt.title('Node rewards over time.')
    plt.legend()
    plt.savefig(save_path)
    plt.clf()


"""Function creates a plot of the node id's that are present in the node_list(s).
:param save_path: The path where the result graphs need to be saved.
:param rewards: The reward dictionary.
:param extra_rewards: The rewards of other praties in the network.
:param node_list: The list of nodes of which one want the corresponding rewards plotted.
:param extra_node_list: The list of nodes of which one want the corresponding rewards plotted.
:returns: Void.
"""
def plot_multiple_rewards_graph(save_path, rewards, extra_rewards, node_list, extra_node_list, xaxis=None, x_ticks=None,
                                marker_list=['o', '^', 'D'], extra_labels=None, labels=None):
    plt.figure(figsize=(6.4, 4.8))
    if xaxis is None:
        #  xaxis is interval [1, #iterations]
        xaxis = range(1, len(rewards[list(node_list)[0]]) + 1)
    for i in range(len(extra_node_list)):
        extra_node = extra_node_list[i]
        data = extra_rewards[extra_node]
        label = "Baseline node %s" % extra_node
        if labels is not None:
            label = labels[i]
        plt.plot(xaxis, data, label=label, marker=marker_list[0])
    for i in range(len(node_list)):
        label = "Node %s" % node_list[i]
        if extra_labels is not None:
            label = extra_labels[i]
        plt.plot(xaxis, rewards[node_list[i]], label=label, alpha=0.7, marker=marker_list[i+1])

    if x_ticks is not None:
        plt.xticks(xaxis, x_ticks, rotation=40, ha="center")
    plt.xlabel('Time (# Iteration)')
    plt.ylabel('Reward (#Milli Satoshi\'s)')
    plt.title('Node rewards over time.')
    plt.legend()
    plt.savefig(save_path)
    plt.clf()
    return

def plot_overlay_rewards_graph(save_path, rewards, extra_rewards, node_list, extra_node_list, xaxis=None, x_ticks=None,
                                marker_list=['o', '^', 'D'], extra_labels=None, labels=None):
    fig, ax1 = plt.subplots(figsize=(6.4, 4.8))
    if xaxis is None:
        xaxis = range(1, len(rewards[list(node_list)[0]]) + 1)

    color = 'tab:blue'
    extra_node = extra_node_list[0]
    data = extra_rewards[extra_node]
    label = extra_labels[0]
    ax1.plot(xaxis, data, color=color, label=label, marker=marker_list[0])
    ax1.set_xlabel('Time (# Iteration)')
    ax1.set_ylabel('Reward (#Milli Satoshi\'s)')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.legend(loc="upper left")

    color = 'tab:red'
    ax2 = ax1.twinx()
    label = labels[0]
    ax2.plot(xaxis, rewards[node_list[0]], color=color, label=label, marker=marker_list[1])
    ax2.set_ylabel('Reward (#Milli Satoshi\'s)')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.legend(loc="upper right")

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    if x_ticks is not None:
        fig.xticks(xaxis, x_ticks, rotation=40, ha="center")
    plt.title('Node rewards over time.')
    plt.savefig(save_path)
    plt.clf()


"""Function writes the rewards dictionairy as a json file to the requested datapath.

:param rewards: The reward dictionary.
:param data_path: The path to which to write the file to.
:param data_filename: The filename to be written to.
:returns: Void.
"""
def write_rewards_graph_data(rewards, data_path, data_filename):
    write_json(rewards, data_path+data_filename)
    print("Written rewards data to file:", data_path+data_filename)
    return


"""Function that parses a json file to a .gml of a graph object.

:param data_path: Data path from the root of the project folder to the json file.
:param data_filename: The json file name.
:param tx_amts: The fixed transaction size that will be used to calculate the edge weights within the model.
:returns: Void.
"""
def convert_json_to_graph(data_path, data_filename, tx_amts):
    data = read_json(data_path + data_filename)

    key_to_node = {}
    node_to_key = {}

    # Simplify node ID's by map
    pub_keys = [node['pub_key'] for node in data['nodes']]
    node_ids = list(range(0, len(pub_keys)))

    # Fill dictionary maps
    for i in range(0, len(pub_keys)):
        key = pub_keys[i]
        key_to_node[str(key)] = i
        node_to_key[str(i)] = key

    write_json(key_to_node, data_path + "key_to_node_map.json")
    write_json(node_to_key, data_path + "node_to_key_map.json")

    # Parse graph
    for tx_amt in tx_amts:
        print("Starting graph parsing:", tx_amt)
        graph = nx.DiGraph()
        graph.add_nodes_from(node_ids)

        # Convert edges from JSON
        for e in data['edges']:
            # If the edge meets the capacity requirements
            if tx_amt <= int(e["capacity"]):
                u = e['node1_pub']
                v = e['node2_pub']
                node_pol1 = e['node1_policy']
                node_pol2 = e['node2_policy']

                # Make 2 directional edges based on the 2 node policies
                if u in key_to_node and v in key_to_node and node_pol1 is not None and node_pol2 is not None:
                    fee = int(node_pol1['fee_base_msat']) + int(node_pol1['fee_rate_milli_msat']) * tx_amt * 0.001
                    graph = add_edge(graph, key_to_node[u], key_to_node[v], fee, False)

                    fee = int(node_pol2['fee_base_msat']) + int(node_pol2['fee_rate_milli_msat']) * tx_amt * 0.001
                    graph = add_edge(graph, key_to_node[v], key_to_node[u], fee, False)

        largest_subgraph = max(list(nx.strongly_connected_components(graph)), key=len)
        graph = graph.subgraph(largest_subgraph)

        nx.write_gml(graph, data_path + "graph" + str(tx_amt) + ".gml")


"""Function that calculates the edge betweenness scores of a graph.
:param graph: The graph to compute the scores on.
:returns: edge betweenness dictionary.
"""
def edge_betweenness_centrality(graph):
    nodes = graph.nodes()
    edges = graph.edges()
    edge_betweenness_dict = {}
    for edge in edges:
        edge_betweenness_dict[edge] = 0

    for src_node in nodes:
        for dst_node in nodes:
            if src_node != dst_node:
                paths = nx.all_shortest_paths(graph, src_node, dst_node, weight='weight')
                paths_to_parse = []
                path_amount = 0
                for path in paths:
                    paths_to_parse.append(path)
                    path_amount += 1
                path_weight = 1 / path_amount

                for path in paths_to_parse:
                    for path_index in range(len(path) - 1):
                        local_src = path[path_index]
                        local_dst = path[path_index + 1]
                        edge_betweenness_dict[(local_src, local_dst)] += path_weight
    return edge_betweenness_dict


"""Function connects a previously not connected party to the network.
:param g: The graph to connect the party to.
:param node_id: The ID that needs to be connected.
:param placement_amt: The number of connection that this method will create.
:param needs_optimization: Boolean to indicate if the edges need to have their fee optimized.
:returns: Graph with the party connected to it.
"""
def initial_connection(g, node_id, placement_amt, needs_optimization):
    deg_list = sorted(g.degree(), key=lambda node: node[1], reverse=True)

    if deg_list[0][0] != node_id:
        choices = [deg_list[0][0]]
    else:
        choices = [deg_list[1][0]]

    for pick_num in range(placement_amt - 1):
        choices.append(pick_initial_connection(g, choices, deg_list, node_id))

    choices = [i for i in choices if i is not None]
    print("Choice: ", choices)

    g = placement_strategies.create_edges(g, choices, node_id, False)
    # Seems to do double work, but if you optimize the first edge created before placing down a second one, it creates
    # an edge with max fee ruining the result.
    if needs_optimization:
        for choice in choices:
            g = placement_strategies.create_edges(g, [choice], node_id, True)
    return g

"""Function that picks candidates that created connection to.
:param g: The graph to analyse for candidates.
:param chosen: The ID's of parties already chosen to be connected to.
:param deg_list: Sorted list of the degree of all parties within the network.
:param node_id: The ID of the source to make connections for.
:returns: The candidate ID.
"""
def pick_initial_connection(g, chosen, deg_list, node_id):
    for node in deg_list:
        choice_id = node[0]
        if choice_id not in chosen and choice_id != node_id:
            if is_not_connected(g, chosen, choice_id):
                return choice_id
    return

"""Function that checks if two parties are not directly connected.
:param g: The graph to analyse.
:param chosen: The source the method is analysing.
:param node_id: The destination the method is analysing.
:returns: A boolean indicating whether the.
"""
def is_not_connected(g, chosen, node_id):
    res = True

    for node in chosen:
        for (src, dst) in g.out_edges([node]):
            if dst is node_id:
                print("%s -> %s exists, failing connectivity check." % (node, node_id))
                res = False
    return res
