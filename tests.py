import unittest
import networkx as nx
import scripts
import fee_strategies
import placement_strategies

node_placement_amt = 2
extra_party_amount = 1

data_path = 'data/barabasi/'
tx_amts = [100, 10000, 1000000]


class Testing(unittest.TestCase):

    ######################### Tests for script.py #########################

    def test_script_get_edge(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        our_party_id = list(g.nodes())[-1]

        edge = scripts.get_edge(g, our_party_id, '0')
        self.assertEqual(edge[0], our_party_id)
        self.assertEqual(edge[1], '0')
        self.assertEqual(edge[2]['weight'], 1000)

    def test_script_add_edge(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        self.assertNotIn(('0', '18'), g.edges())

        g = scripts.add_edge(g, '0', '18', 1000, False)
        self.assertIn(('0', '18', {'weight': 1000}), g.edges(data=True))

    def test_script_remove_edge(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        self.assertIn(('2', '0'), g.edges())

        g = scripts.remove_edge(g, '2', '0')
        self.assertNotIn(('2', '0'), g.edges())
        self.assertNotIn(('0', '2'), g.edges())

    def test_script_add_node(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        self.assertNotIn('21', g.nodes())

        g, new_node_id = scripts.add_node(g)
        self.assertIn(new_node_id, g.nodes())

    def test_script_init_reward_list(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        rewards = None
        self.assertIsNone(rewards)

        rewards = scripts.init_reward_list(g)
        self.assertIsNotNone(rewards)
        self.assertEqual(len(rewards.keys()), len(g.nodes))

    def test_script_calc_node_profit(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        rewards = scripts.init_reward_list(g)
        self.assertIsNotNone(rewards)

        rewards = scripts.calc_node_profit(g, rewards)
        self.assertEqual(len(rewards['0']), 1)
        self.assertEqual(rewards['0'][0], 39881.5)

    def test_script_edge_betweenness_centrality(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")

        edge_betweenness_dict = scripts.edge_betweenness_centrality(g)
        self.assertEqual(len(edge_betweenness_dict), 154)
        self.assertEqual(edge_betweenness_dict[('0', '7')], 3.0)

    def test_script_initial_connection_base(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        new_node = scripts.add_node(g)
        self.assertEqual(len(g.out_edges(new_node)), 0)

        g = scripts.initial_connection(g, new_node, 1, False)
        self.assertEqual(len(g.out_edges(new_node)), 1)

    def test_script_initial_connection_multiple(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        new_node = scripts.add_node(g)
        self.assertEqual(len(g.out_edges(new_node)), 0)

        g = scripts.initial_connection(g, new_node, 2, False)
        self.assertEqual(len(g.out_edges(new_node)), 2)

    def test_script_is_not_connected(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        new_node = scripts.add_node(g)

        isNotConnected = scripts.is_not_connected(g, ['1'], new_node)
        self.assertTrue(isNotConnected)

        g = scripts.add_edge(g, new_node, '1', 1000, False)
        g = scripts.add_edge(g, '1', new_node, 1000, False)
        isNotConnected = scripts.is_not_connected(g, ['1'], new_node)
        self.assertFalse(isNotConnected)

    ######################### Tests for placement_strategies.py #########################

    def test_placement_strategies_set_most_freq_fee(self):
        global tx_most_freq_fees
        global most_freq_fee
        self.assertEqual(fee_strategies.most_freq_fee, -1)

        fee_strategies.set_most_freq_fee(100)
        self.assertEqual(fee_strategies.most_freq_fee, 1000.0)

    def test_placement_strategies_remove_connected_nodes(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        our_party_id = list(g.nodes())[-1]
        self.assertEqual(len(g.nodes()), 21)

        new_connections = placement_strategies.remove_connected_nodes(g.nodes(), g.edges(), our_party_id)
        self.assertEqual(len(new_connections), 18)

    def test_placement_strategies_create_edges_base(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        g, new_node_id = scripts.add_node(g)

        g = placement_strategies.create_edges(g, ['1'], new_node_id, False, 1050)
        edge = scripts.get_edge(g, new_node_id, '1')
        self.assertEqual(edge[0], new_node_id)
        self.assertEqual(edge[1], '1')
        self.assertEqual(edge[2]['weight'], 1050)

    def test_placement_strategies_uniform_random(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        g, new_node_id = scripts.add_node(g)
        scripts.initial_connection(g, new_node_id, 2, True)

        g = placement_strategies.uniform_random(g, new_node_id, 1, True, seed=43)
        edge = scripts.get_edge(g, new_node_id, '10')
        self.assertNotEqual(edge, -1)
        self.assertEqual(edge[0], new_node_id)
        self.assertEqual(edge[1], '10')

    def test_placement_strategies_highest_degree(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        g, new_node_id = scripts.add_node(g)
        scripts.initial_connection(g, new_node_id, 2, True)

        g = placement_strategies.highest_degree(g, new_node_id, 1, True)
        print(g.out_edges(new_node_id))
        edge = scripts.get_edge(g, new_node_id, '6')
        self.assertNotEqual(edge, -1)
        self.assertEqual(edge[0], new_node_id)
        self.assertEqual(edge[1], '6')

    def test_placement_strategies_betweenness_centrality(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        g, new_node_id = scripts.add_node(g)
        scripts.initial_connection(g, new_node_id, 2, True)

        g = placement_strategies.betweenness_centrality(g, new_node_id, 1, True)
        print(g.out_edges(new_node_id))
        edge = scripts.get_edge(g, new_node_id, '6')
        self.assertNotEqual(edge, -1)
        self.assertEqual(edge[0], new_node_id)
        self.assertEqual(edge[1], '6')

    def test_placement_strategies_k_center(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        g, new_node_id = scripts.add_node(g)
        scripts.initial_connection(g, new_node_id, 2, True)

        g = placement_strategies.k_center(g, new_node_id, 1, True)
        print(g.out_edges(new_node_id))
        edge = scripts.get_edge(g, new_node_id, '11')
        self.assertNotEqual(edge, -1)
        self.assertEqual(edge[0], new_node_id)
        self.assertEqual(edge[1], '11')

    def test_placement_strategies_k_means(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        g, new_node_id = scripts.add_node(g)
        scripts.initial_connection(g, new_node_id, 2, True)

        g = placement_strategies.k_means(g, new_node_id, 1, True)
        print(g.out_edges(new_node_id))
        edge = scripts.get_edge(g, new_node_id, '20')
        self.assertNotEqual(edge, -1)
        self.assertEqual(edge[0], new_node_id)
        self.assertEqual(edge[1], '20')

    def test_placement_strategies_fee_weighted_centrality(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        placement_strategies.set_most_freq_fee(100)
        g, new_node_id = scripts.add_node(g)
        scripts.initial_connection(g, new_node_id, 2, True)

        g = placement_strategies.fee_weighted_centrality(g, new_node_id, 1)
        print(g.out_edges(new_node_id))
        edge = scripts.get_edge(g, new_node_id, '3')
        self.assertNotEqual(edge, -1)
        self.assertEqual(edge[0], new_node_id)
        self.assertEqual(edge[1], '3')

    ######################### Tests for fee_strategies.py #########################

    def test_fee_strategies_graph_fee_optimization(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        our_party_id = list(g.nodes())[-1]
        self.assertEqual(scripts.get_edge(g, '0', '1')[2]['weight'], 1402)
        g = fee_strategies.graph_fee_optimization(g)
        self.assertEqual(scripts.get_edge(g, '0', '1')[2]['weight'], 563)

    def test_fee_strategies_edge_fee_optimization(self):
        g = nx.read_gml(
data_path + "randomness_graphs/scenario2/" + "medium-graph" + str(tx_amts[2]) + "_init" + ".gml")
        our_party_id = list(g.nodes())[-1]
        for e in g.out_edges(our_party_id, data=True):
            g = scripts.add_edge(g, e[0], e[1], int(e[2]['weight'] / 2), False)

        edge = scripts.get_edge(g, our_party_id, '0')
        best_rew = 871.0  # precomputed value
        best_fee = 828  # precomputed value

        g = fee_strategies.edge_fee_optimization(g, edge)
        edge_after_optimization = scripts.get_edge(g, our_party_id, '0')
        self.assertEqual(edge[2]['weight'], edge_after_optimization[2]['weight'])

    def test_fee_strategies_compute_node_rew(self):
        g = nx.read_gml(data_path + "randomness_graphs/scenario2/" + "small-graph" + str(tx_amts[0]) + "_init" + ".gml")
        edge = scripts.get_edge(g, '0', '1')

        edge_rew, rest_rew = fee_strategies.compute_node_rew(1001, g, edge)
        self.assertEqual(edge_rew, 0.0)
        self.assertEqual(rest_rew, 39881.5)


if __name__ == '__main__':
    unittest.main()
