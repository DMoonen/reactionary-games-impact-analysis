import networkx as nx
import scripts
import fee_strategies
import placement_strategies

node_placement_amt = 5

data_path = 'data/barabasi/'
tx_amts = [100, 10000, 1000000]

if __name__ == '__main__':
    for tx_amount in tx_amts:
        """ Game Theory """
        print("Game Theory Network, tx:", tx_amount, flush=True)

        print("Loading graph...", flush=True)
        # Load in the graph where we have already been added with 2 connections.
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "medium-graph" + str(tx_amount) + "_init" + ".gml")
        our_party_id = list(g.nodes())[-1]
        print("Graph loaded...", flush=True)

        fee_strategies.set_most_freq_fee(tx_amount)
        placement_strategies.set_most_freq_fee(tx_amount)

        # Created the rewards table after all new parties have been created.
        rewards = scripts.init_reward_list(g)
        # Initialize the rewards table with the rewards from initial connections.
        rewards = scripts.calc_node_profit(g, rewards)

        minimum_reward_check = []

        # Place the channels.
        for node in range(node_placement_amt):
            print("Placing connection #%s for 'our' node." % (node + 1), flush=True)
            # scenario_info here is used a flag, since the network scenario does rely on values in the dict,
            # only the key "network" needs to be present.
            scenario_info = {"network": 'x'}
            g, chosen_candid = placement_strategies.game_theory(g, our_party_id, 1, scenario_info)
            print(g.edges(data=True))
            print("Connection #%s placed for 'our' node." % (node + 1), flush=True)

            # Calculate rewards after placing connections
            rewards = scripts.calc_node_profit(g, rewards)

            print("Starting to optimize the whole graph", flush=True)
            g = fee_strategies.graph_fee_optimization(g)
            print("Finished optimizing the whole graph", flush=True)

            # Calculate rewards after placing connections
            rewards = scripts.calc_node_profit(g, rewards)

            comparison = [chosen_candid[5], list(rewards[our_party_id])[-1],
                          chosen_candid[5] <= list(rewards[our_party_id])[-1]]
            minimum_reward_check.append(comparison)

        # Write to file
        scripts.write_rewards_graph_data(rewards, data_path + "results/",
                                         "rewards_game_theory_network_" + str(tx_amount)
                                         + "_randomness_scenario_2.json")
        scripts.write_rewards_graph_data(minimum_reward_check, data_path + "results/",
                                         "rewards_game_theory_network_" + str(tx_amount)
                                         + "_randomness_minimum_value_check.json")

