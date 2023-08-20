import networkx as nx
import scripts
import fee_strategies
import placement_strategies

node_placement_amt = 5
extra_party_amount = 1

data_path = 'data/barabasi/'
tx_amts = [100, 10000, 1000000]

if __name__ == '__main__':
    for tx_amount in tx_amts:
        """ Scenario 4 """
        print("Scenario 4, tx:", tx_amount, flush=True)

        # Load the graph
        print("Loading graph...", flush=True)
        # Load in the graph where 2 parties have already been added with 2 connections.
        g = nx.read_gml(data_path + "randomness_graphs/scenario4/" + "graph" + str(tx_amount) + "_" +
                        str(extra_party_amount) + "_party_init" + ".gml")

        # Obtain our  party ID's
        our_party_id = list(g.nodes())[-(extra_party_amount + 1)]
        other_id_list = []
        for i in range(extra_party_amount):
            other_id_list.append(list(g.nodes())[-(i + 1)])
        print("Graph loaded...", flush=True)

        fee_strategies.set_most_freq_fee(tx_amount)
        placement_strategies.set_most_freq_fee(tx_amount)

        # Created the rewards table after all new parties have been created.
        rewards = scripts.init_reward_list(g)
        # Initialize the rewards table with the rewards from initial connections.
        rewards = scripts.calc_node_profit(g, rewards)

        # Place the channels.
        for node in range(node_placement_amt):
            print("Placing connection #%s for 'our' node." % (node + 1), flush=True)
            g = placement_strategies.fee_weighted_centrality(g, our_party_id, 1)
            print("Connection #%s placed for 'our' node." % (node + 1), flush=True)
            
            rewards = scripts.calc_node_profit(g, rewards)

            print("Starting to optimize the graph...", flush=True)
            g = fee_strategies.graph_fee_optimization(g)
            print("Finished optimizing the graph...", flush=True)
	    
            rewards = scripts.calc_node_profit(g, rewards)
            
            # Place other party channels.
            for other_id in other_id_list:
                print("Placing connection #%s for 'other' ID=%s." % (node + 1, other_id), flush=True)
                g = placement_strategies.fee_weighted_centrality(g, other_id, 1)
                print("Connection #%s placed for 'other' ID=%s." % (node + 1, other_id), flush=True)
                
                rewards = scripts.calc_node_profit(g, rewards)

                print("Starting to optimize the graph...", flush=True)
                g = fee_strategies.graph_fee_optimization(g)
                print("Finished optimizing the graph...", flush=True)

                rewards = scripts.calc_node_profit(g, rewards)

        # Write to file
        scripts.write_rewards_graph_data(rewards, data_path + "results/", "rewards_fee_weighted_centrality_" + str(tx_amount)
                                         + "_randomness_scenario_4.json")
