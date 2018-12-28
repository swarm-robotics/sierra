"""
 Copyright 2018 London Lowmanstone, John Harwell, All rights reserved.

  This file is part of SIERRA.

  SIERRA is free software: you can redistribute it and/or modify it under the
  terms of the GNU General Public License as published by the Free Software
  Foundation, either version 3 of the License, or (at your option) any later
  version.

  SIERRA is distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
  A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with
  SIERRA.  If not, see <http://www.gnu.org/licenses/
"""

import os
import random
import pickle
from pipeline.xml_luigi import XMLLuigi, InvalidElementError
from variables import time_setup


class ExpInputGenerator:

    """
    Base class for generating:

    1. A set of ARGoS simulation input files from a template for a *single* experiment.
    2. A command file with commands to run each simulation suitable for input into GNU Parallel for
       a *single* experiment.

    Attributes:
      template_config_path(str): Path(relative to current dir or absolute) to the template XML
                                 configuration file.
      generation_root(str): Where generated XML input files for ARGoS for this experiment should be
                            stored(relative to current dir or absolute).
      exp_output_root(str): Root directory for simulation outputs for this experiment (sort of a
                            scratch directory). Can be relative or absolute.
      exp_def_fname(str): Name of file to use for pickling experiment definitions.
      sim_opts(dict): Dictionary containing the following keys:
                      n_sims : # of simulations to run in parallel
                      n_threads: # of ARGoS threads to use for each parallel simulation
                      tsetup: Name of class in time_setup.py to use for simulation time setup.
                      n_physics_engines: # of ARGoS physics engines to use.
                      arena_dim: (X,Y) dimensions of the arena.
                      with_robot_rab(bool): Should the range and bearing sensors/actuators be
                                            enabled?
                      with_robot_leds(bool): Should the LED actuators be enabled?
                      with_robot_battery(bool): Should the battery sensor be enabled?
    """

    def __init__(self, template_config_file, generation_root, exp_output_root, exp_def_fname,
                 sim_opts):
        assert os.path.isfile(template_config_file), \
            "The path '{}' (which should point to the main config file) did not point to a file".format(
                template_config_file)
        self.template_config_file = os.path.abspath(template_config_file)

        # will get the main name and extension of the config file (without the full absolute path)
        self.main_config_name, self.main_config_extension = os.path.splitext(
            os.path.basename(self.template_config_file))

        # where the generated config and command files should be stored
        self.generation_root = os.path.abspath(generation_root)

        assert self.generation_root.find(" ") == -1, \
            ("ARGoS (apparently) does not support running configuration files with spaces in the " +
             "Please make sure the configuration file save path '{}' does not have any spaces in it").format(self.generation_root)

        self.exp_output_root = os.path.abspath(exp_output_root)
        self.sim_opts = sim_opts
        self.exp_def_fpath = os.path.join(self.generation_root, exp_def_fname)

        self.random_seed_min = 1
        self.random_seed_max = 10 * self.sim_opts["n_sims"]

        # where the commands file will be stored
        self.commands_fpath = os.path.abspath(
            os.path.join(self.generation_root, "commands.txt"))

        # to be formatted like: self.config_name_format.format(name, experiment_number)
        format_base = "{}_{}"
        self.config_name_format = format_base + self.main_config_extension
        self.output_name_format = format_base + "_output"

    def init_sim_defs(self):
        """Generates simulation definitions common to all simulations."""
        # create an object that will edit the XML file
        xml_luigi = XMLLuigi(self.template_config_file)

        # make the save path
        os.makedirs(self.generation_root, exist_ok=True)

        # Clear out commands_path if it already exists
        if os.path.exists(self.commands_fpath):
            os.remove(self.commands_fpath)

        # Setup simulation visualizations
        self._init_visualization_defs(xml_luigi)

        # Setup threading
        self._init_threading_defs(xml_luigi)

        # Setup robot sensors/actuators
        self._init_sa_defs(xml_luigi)

        # Setup simulation time parameters
        self._init_time_defs(xml_luigi)

        return xml_luigi

    def _init_time_defs(self, xml_luigi):
        """
        Setup simulation time parameters and write them to the pickle file for retrieval during
        graph generation later.
        """
        setup = __import__("variables.{0}".format(
            self.sim_opts["tsetup"].split(".")[0]), fromlist=["*"])
        tsetup_inst = getattr(setup, "Factory")(self.sim_opts["tsetup"])()
        for a in tsetup_inst.gen_attr_changelist()[0]:
            xml_luigi.attribute_change(a[0], a[1], a[2])

        # Write time setup  info to file for later retrieval
        with open(self.exp_def_fpath, 'ab') as f:
            pickle.dump(tsetup_inst.gen_attr_changelist()[0], f)

    def _init_sa_defs(self, xml_luigi):
        """
        Disable selected sensors/actuators, which are computationally expensive in large swarms, but
        not that costly if the # robots is small.
        """
        if not self.sim_opts["with_robot_rab"]:
            xml_luigi.tag_remove(".//media", "range_and_bearing")
            xml_luigi.tag_remove(".//actuators", "range_and_bearing")
            xml_luigi.tag_remove(".//sensors", "range_and_bearing")

        if not self.sim_opts["with_robot_leds"]:
            xml_luigi.tag_remove(".//actuators", "leds")

        if not self.sim_opts["with_robot_battery"]:
            xml_luigi.tag_remove(".//sensors", "battery")
            xml_luigi.tag_remove(".//entity/foot-bot", "battery")

    def _init_threading_defs(self, xml_luigi):
        """
        Set the # of cores for a simulation to use, which may be less than the total # available on
        the system.
        """
        xml_luigi.attribute_change(".//system",
                                   "threads",
                                   str(self.sim_opts["n_threads"]))
        xml_luigi.attribute_change(".//loop_functions/convergence",
                                   "n_threads",
                                   str(self.sim_opts["n_threads"]))

    def _init_visualization_defs(self, xml_luigi):
        """
        Remove visualization elements from input file, if configured to do so. It may be desired to
        leave them in if generating frames/video.
        """
        if self.sim_opts["with_visualizations"] == "none" or self.sim_opts["with_visualizations"] == "argos":
            self._remove_xml_elements(xml_luigi, [("./loop_functions", "./visualization")])

        if self.sim_opts["with_visualizations"] == "none" or self.sim_opts["with_visualizations"] == "fordyca":
            self._remove_xml_elements(xml_luigi, [(".", "./visualization")])

    def _create_all_sim_inputs(self, random_seeds, xml_luigi):
        """Generate and the input files for all simulation runs."""

        for exp_num in range(self.sim_opts["n_sims"]):
            self._create_sim_input_file(random_seeds, xml_luigi, exp_num)
            self._add_sim_to_command_file(os.path.join(self.generation_root,
                                                       self.config_name_format.format(
                                                           self.main_config_name, exp_num)))

    def _create_sim_input_file(self, random_seeds, xml_luigi, exp_num):
        """Generate and write the input files for a particular simulation run."""

        # create a new name for this experiment's config file
        new_config_name = self.config_name_format.format(
            self.main_config_name, exp_num)

        # get the random seed for this experiment
        random_seed = random_seeds[exp_num]

        # set the random seed in the config file
        # restriction: the config file must have these fields in order for this function to work
        # correctly.
        xml_luigi.attribute_change(".//experiment", "random_seed", str(random_seed))

        # set the output directory
        # restriction: these attributes must exist in the config file
        # this should throw an error if the attributes don't exist
        output_dir = self.output_name_format.format(
            self.main_config_name, exp_num)
        xml_luigi.attribute_change(
            ".//controllers/*/params/output/sim", "output_dir", output_dir)
        xml_luigi.attribute_change(
            ".//controllers/*/params/output/sim", "output_root", self.exp_output_root)
        xml_luigi.attribute_change(
            ".//loop_functions/output/sim", "output_dir", output_dir)
        xml_luigi.attribute_change(
            ".//loop_functions/output/sim", "output_root", self.exp_output_root)
        save_path = os.path.join(
            self.generation_root, new_config_name)
        xml_luigi.output_filepath = save_path
        open(save_path, 'w').close()  # create an empty file
        # save the config file to the correct place
        xml_luigi.write()

    def _remove_xml_elements(self, xml_luigi, remove_list):
        """Generates and saves all the XML config files for all the experiments"""

        for item in remove_list:
            try:
                xml_luigi.tag_remove(item[0], item[1])
            except InvalidElementError:
                # it's okay if this one doesn't exist
                print("XML elements '{}' not found: not removed.".format(item))
                pass

    def _add_sim_to_command_file(self, xml_fname):
        """Adds the command to run a particular simulation definition to the command file."""
        # need the double quotes around the path so that it works in both Linux and Windows
        with open(self.commands_fpath, "a") as commands_file:
            commands_file.write(
                'argos3 -c "{}" --log-file /dev/null --logerr-file /dev/null\n'.format(xml_fname))

    def _generate_random_seeds(self):
        """Generates random seeds for experiments to use."""
        try:
            return random.sample(range(self.random_seed_min, self.random_seed_max + 1), self.sim_opts["n_sims"])
        except ValueError:
            # create a new error message that clarifies the previous one
            raise ValueError("Too few seeds for the required experiment amount; change the random seed parameters") from None
