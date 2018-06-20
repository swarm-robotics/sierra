'''
By: London Lowmanstone
'''

import os
import random
import argparse
import subprocess
import re
from csv_class import CSV
from xml_helper import XMLHelper, InvalidElementError

class ExperimentRunner:
    def __init__(self, config_path, code_path, config_save_path, output_save_path, graph_save_path, amount, random_seed_min=None, random_seed_max=None,
                 remove_both_visusalizations=False):
        # where the main config file is
        assert os.path.isfile(config_path), "The path '{}' (which should point to the main config file) did not point to a file".format(config_path)
        self.config_path = os.path.abspath(config_path)

        # will get the main name and extension of the config file (without the full absolute path)
        self.main_config_name, self.main_config_extension = os.path.splitext(os.path.basename(self.config_path))

        # where the code for the experiment is
        self.code_path = os.path.abspath(code_path)

        # where the generated config and command files should be stored
        if config_save_path is None:
            config_save_path = os.path.join(os.path.dirname(self.config_path), "Generated_Config_Files")
        self.config_save_path = os.path.abspath(config_save_path)

        assert self.config_save_path.find(" ") == -1, ("Argos does not support running configuration files with spaces in the path. Please make sure the "+
                                                       "configuration file save path '{}' does not have any spaces in it").format(self.config_save_path)

        # where the output data should be stored
        if output_save_path is None:
            output_save_path = os.path.join(os.path.dirname(self.config_save_path), "Generated_Output")
        self.output_save_path = os.path.abspath(output_save_path)

        # where the graphs should be stored
        if graph_save_path is None:
            graph_save_path = os.path.join(os.path.dirname(self.config_save_path), "Generated_Graph_Files")
        self.graph_save_path = os.path.abspath(graph_save_path)

        # how many experiments should be run
        self.amount = amount

        # the minimum and maximum random seeds for the experiments
        # default: choose random seeds from 1 to 10 times the amount of experiments
        if random_seed_min is None:
            random_seed_min = 1
        if random_seed_max is None:
            random_seed_max = 10 * self.amount
        self.random_seed_min = random_seed_min
        self.random_seed_max = random_seed_max

        # whether or not it should remove the loop-function visualization (as well as the main argos visualization)
        self.remove_both_visusalizations = remove_both_visusalizations

        # where the commands file will be stored
        self.commands_file_path = os.path.abspath(os.path.join(self.config_save_path, "commands.txt"))

        # to be formatted like: self.config_name_format.format(name, experiment_number)
        format_base = "{}_{}"
        self.config_name_format = format_base + self.main_config_extension
        self.output_name_format = format_base + "_output"


    def generate_xml_files(self):
        xml_helper = XMLHelper(self.config_path)

        # make the save path
        os.makedirs(self.config_save_path, exist_ok=True)

        try:
            xml_helper.remove_element("argos-configuration.visualization")
        except InvalidElementError:
            # it's okay if this one doesn't exist
            pass

        if self.remove_both_visusalizations:
            try:
                xml_helper.remove_element("loop_functions.visualization")
            except InvalidElementError:
                print("Note: it was specified to remove both visualizations, but the second visualization was not found")

        try:
            random_seeds = self._generate_random_seeds()
        except ValueError:
            # create a new error message that clarifies the previous one
            raise ValueError("Too few seeds for the required experiment amount; change the random seed parameters") from None

        with open(self.commands_file_path, "w") as commands_file:
            for experiment_number in range(self.amount):
                new_config_name = self.config_name_format.format(self.main_config_name, experiment_number)
                random_seed = random_seeds[experiment_number]
                # restriction: the config file must have these fields in order for this function to work correctly.
                xml_helper.set_attribute("experiment.random_seed", random_seed)

                # set the output directory
                # restriction: these attributes must exist in the config file
                # this should throw an error if the attributes don't exist
                output_dir = self.output_name_format.format(self.main_config_name, experiment_number)
                xml_helper.set_attribute("controllers.output.sim.output_dir", output_dir)
                xml_helper.set_attribute("controllers.output.sim.output_root", self.output_save_path)
                xml_helper.set_attribute("loop_functions.output.sim.output_dir", output_dir)
                xml_helper.set_attribute("loop_functions.output.sim.output_root", self.output_save_path)
                save_path = os.path.join(self.config_save_path, new_config_name)
                open(save_path, 'w').close() # create an empty file
                xml_helper.write(save_path)
                # need the double quotes around the path so that it works in both Linux and Windows
                commands_file.write('argos3 -c "{}"\n'.format(save_path))
        print("The XML files have been generated.")


    def run_experiments(self, personal=False):
        try:
            if personal:
                subprocess.run('cd "{}" && parallel < "{}"'.format(self.code_path, self.commands_file_path), shell=True, check=True)
            else:
                subprocess.run('cd "{}" && module load parallel && sort -u $PBS_NODEFILE > unique-nodelist.txt && \
                                parallel --jobs 1 --sshloginfile unique-nodelist.txt --workdir $PWD < "{}"'.format(self.code_path, self.commands_file_path),
                               shell=True, check=True)
            print("Experiments ran successfully. (Output can be found in '{}')".format(runner.code_path))
        except subprocess.CalledProcessError as e:
            print("Experiments failed.")
            raise e

    def average_csvs(self):
        csvs = {}
        pattern = self.output_name_format.format(re.escape(self.main_config_name), "\d+")
        for entry in os.scandir(self.output_save_path):
            if re.fullmatch(pattern, entry.name):
                # restriction: csv files must be in the "metrics" folder inside the output folder
                # TODO check with John to see if that's a good restriction
                for inner_entry in os.scandir(os.path.join(entry.path, "metrics")):
                    if inner_entry.name.endswith(".csv"):
                        csv = CSV(inner_entry.path, delimiter=";")
                        if inner_entry.name not in csvs:
                            csvs[inner_entry.name] = []
                        csvs[inner_entry.name].append(csv)
        averaged_csvs = {key:self._average_csvs(csvs[key]) for key in csvs}
        csvs_path = os.path.join(self.output_save_path, "Averaged_Output")
        os.makedirs(csvs_path, exist_ok=True)
        for name, value in averaged_csvs.items():
            value.write(os.path.join(csvs_path, name))
        print("The CSVs have been averaged. (Output can be found in '{}')".format(csvs_path))


    def _average_csvs(self, csvs):
        '''
        Takes a list of csvs and averages them.
        Returns None if the list is empty
        '''
        if not csvs:
            return None
        csv_sum = csvs[0]
        for index in range(1, len(csvs)):
            csv_sum += csvs[index]
        return csv_sum / len(csvs)


    def _generate_random_seeds(self):
        return random.sample(range(self.random_seed_min, self.random_seed_max + 1), self.amount)


if __name__ == "__main__":
    # check python version
    import sys
    if sys.version_info < (3, 0):
        raise RuntimeError("Python 3.x should be usued to run this code.")
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path", help="the configuration file for the experiment to be run")
    parser.add_argument("code_path", help="where the code is to run the experiment")
    parser.add_argument("amount", help="how many experiments to run (specify 0 to just average CSVs and create graphs "+
                                       "without generating config files or running experiments)", type=int)
    parser.add_argument("--config_save_path", help="where to save the generated config files")
    parser.add_argument("--output_save_path", help="where to save the generated output")
    parser.add_argument("--graph_save_path", help="where to save the generated graph files")
    run_group = parser.add_mutually_exclusive_group()
    run_group.add_argument("--do_not_run", help="include to only generate the config files and command file, not run them", action="store_true")
    run_group.add_argument("--only_run", help="include to only run the config files, not generate them", action="store_true")
    parser.add_argument("--do_not_average", help="include to not average the CSVs", action="store_true")
    parser.add_argument("--personal", help="include if running parallel on a personal computer (otherwise runs supercomputer commands)", action="store_true")
    parser.add_argument("--random_seed_min", help="the minimum random seed number", type=int)
    parser.add_argument("--random_seed_max", help="the maximum random seed number", type=int)
    parser.add_argument("--remove_both_visuals", help="include to remove the loop function visualization (in addition to the argos visualization)",
                        action="store_true")
    args = parser.parse_args()
    runner = ExperimentRunner(args.config_path, args.code_path, args.config_save_path, args.output_save_path, args.graph_save_path, args.amount,
                              args.random_seed_min, args.random_seed_max, args.remove_both_visuals)

    if (runner.amount > 0):
        if not args.only_run:
            runner.generate_xml_files()
        if not args.do_not_run:
            runner.run_experiments(personal=args.personal)
    if not args.do_not_average:
        runner.average_csvs()
