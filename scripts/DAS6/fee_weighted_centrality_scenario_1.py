import networkx as nx
import scripts
import fee_strategies
import placement_strategies

node_placement_amt = 5

data_path = 'data/barabasi/'
tx_amts = [100, 10000, 1000000]

if __name__ == '__main__':
    for tx_amount in tx_amts:
        """ Scenario 1 """
        print("Scenario 1, tx:", tx_amount, flush=True)
        # Load the graph

        print("Loading graph...", flush=True)
        # Load in the graph where we have already been added with 2 connections
        g = nx.read_gml(data_path + "randomness_graphs/scenario1_optimized/" + "graph" + str(tx_amount) + "_init" + ".gml")
        our_party_id = list(g.nodes())[-1]
        print("Graph loaded...", flush=True)

        fee_strategies.set_most_freq_fee(tx_amount)
        placement_strategies.set_most_freq_fee(tx_amount)

        # Created the rewards table after all new parties have been created
        rewards = scripts.init_reward_list(g)
        # Initialize the rewards table with the rewards from initial connections.
        rewards = scripts.calc_node_profit(g, rewards)

        # Place the channels
        for node in range(node_placement_amt):
            print("Placing connection #%s." % (node + 1), flush=True)
            g = placement_strategies.fee_weighted_centrality(g, our_party_id, 1)
            print("Connection #%s placed." % (node + 1), flush=True)

            # Calculate rewards after placing connections
            rewards = scripts.calc_node_profit(g, rewards)

        # Write to file
        scripts.write_rewards_graph_data(rewards, data_path + "results/", "rewards_fee_weighted_centrality_" + str(tx_amount)
                                         + "_randomness_scenario_1.json")
