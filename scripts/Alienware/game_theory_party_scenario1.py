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
        """ Game Theory """
        print("Game Theory Party, tx:", tx_amount, flush=True)

        print("Loading graph...", flush=True)
        # Load in the graph where we have already been added with 2 connections.
        g = nx.read_gml(data_path + "randomness_graphs/" + "medium-graph" + str(tx_amount) + "_init" + ".gml")
        our_party_id = list(g.nodes())[-1]
        print("Graph loaded...", flush=True)

        fee_strategies.set_most_freq_fee(tx_amount)
        placement_strategies.set_most_freq_fee(tx_amount)

        # Loading in the 'other' parties.
        other_id_list = []
        for i in range(extra_party_amount):
            # Add a party that represents the channels that will be created after us.
            print("Adding 'other' party #%s to the network" % (i + 1), flush=True)
            g, other_party_id = scripts.add_node(g)
            other_id_list.append(other_party_id)

            # Set the same starting connection + weights as that 'our_party' starts with.
            for edge in g.out_edges(our_party_id, data=True):
                for temp_id in other_id_list:
                    g = placement_strategies.create_edges(g, [edge[1]], temp_id, False, given_src_fee=edge[2]['weight'])
            print("Added...", flush=True)

        # Created the rewards table after all new parties have been created.
        rewards = scripts.init_reward_list(g)
        # Initialize the rewards table with the rewards from initial connections.
        rewards = scripts.calc_node_profit(g, rewards)

        minimum_reward_check = []

        # Place the channels.
        for node in range(node_placement_amt):
            print("Placing connection #%s for 'our' node." % (node + 1), flush=True)
            scenario_info = {"party": other_id_list}
            g, chosen_candid = placement_strategies.game_theory(g, our_party_id, 1, scenario_info)
            print("Connection #%s placed for 'our' node." % (node + 1), flush=True)

            # Calculate rewards after placing connections
            rewards = scripts.calc_node_profit(g, rewards)

            # Place other party channels.
            for other_id in other_id_list:
                print("Placing connection #%s for 'other' ID=%s." % (node + 1, other_id), flush=True)
                g = placement_strategies.fee_weighted_centrality(g, other_id, 1)
                print("Connection #%s placed for 'other' ID=%s." % (node + 1, other_id), flush=True)

                # Calculate rewards after placing connections
                rewards = scripts.calc_node_profit(g, rewards)

            edge = scripts.get_edge(g, chosen_candid[0], chosen_candid[1])
            new_fee = edge[2]['weight']
            edge_rew, other_edge_rew = fee_strategies.compute_node_rew(new_fee, g, edge)
            sum_reward = edge_rew + other_edge_rew
            comparison = [chosen_candid[5], sum_reward, chosen_candid[5] <= sum_reward]
            minimum_reward_check.append(comparison)

        # Write to file
        scripts.write_rewards_graph_data(rewards, data_path + "results/",
                                         "rewards_game_theory_party_" + str(tx_amount)
                                         + "_randomness_scenario_1.json")
        scripts.write_rewards_graph_data(minimum_reward_check, data_path + "results/",
                                         "rewards_game_theory_party_" + str(tx_amount)
                                         + "_randomness_minimum_value_check.json")

