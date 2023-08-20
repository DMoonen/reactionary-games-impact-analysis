import os
import json
import scripts

tx_amts = [100, 10000, 1000000]
dir_list = os.listdir()
extra_party_amount = {"_1.json": 0, "_2.json": 0, "_3.json": 1, "_4.json": 1}
scenarios = ["_1.json", "_2.json", "_3.json", "_4.json"]

for item in dir_list:
    print(item)
    for scen_identifier in scenarios:
        if scen_identifier in item:
            output_string = item
            local_extra_party = extra_party_amount[scen_identifier]

            if local_extra_party >= 1:
                print("normalizing data..")
                with open(str(item), 'r') as f:
                    read_data = json.load(f)

                output = {}
                num_keys = len(read_data.keys())

                numerator = (num_keys - local_extra_party) * (num_keys - (2 * local_extra_party))
                denominator = num_keys * (num_keys - local_extra_party)
                ratio = numerator / denominator
                for key in read_data.keys():
                    output[key] = [round(x * ratio, 2) for x in read_data[key]]

                # Write output
                scripts.write_rewards_graph_data(output, "", output_string)
