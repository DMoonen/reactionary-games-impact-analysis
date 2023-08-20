import os
import json
import scripts

tx_amts = [100, 10000, 1000000]
dir_list = os.listdir()
output_string = "rewards_uniform_random_%s_randomness_scenario_%s.json"


def add_lists(lista, listb):
    ret = []
    for i in range(len(lista)):
        ret.append(lista[i] + listb[i])
    if len(listb) > len(lista):
        ret.append(listb[len(lista):])
    return ret


for tx in tx_amts:
    uniform_data = {}

    for item in dir_list:
        if str(tx)+"_" in item:
            ID = item.split('_')[-1].split('.')[0]
            read_data = None
            with open(str(item), 'r') as f:
                read_data = json.load(f)
            uniform_data[ID] = read_data

    dict_key_list = list(uniform_data.keys())
    print(dict_key_list)
    num_dicts = len(dict_key_list)
    print(num_dicts)
    num_values = len(uniform_data[dict_key_list[0]])
    run_amount = len(uniform_data[dict_key_list[0]]['0'])

    # Sum all values
    result_dict = uniform_data[dict_key_list[0]]
    for d_key in dict_key_list[1:]:
        dict = uniform_data[d_key]
        for value_key in dict.keys():
            result_dict[value_key] = add_lists(result_dict[value_key], dict[value_key])

    # Divide to reach average
    for value_key in result_dict.keys():
        result_dict[value_key] = [round(x / num_dicts, 2) for x in result_dict[value_key]]

    #Save
    scenario = dir_list[0].split('_')[-2]
    local_output_string = output_string % (tx, scenario)

    scripts.write_rewards_graph_data(result_dict, "", local_output_string)


