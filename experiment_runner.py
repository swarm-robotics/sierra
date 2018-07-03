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
import subprocess


class ExperimentRunner:

    """
    Runs the specified  # of experiments in parallel using GNU Parallel on
    the provided set of hosts on MSI (or on a single personal computer for testing).

    Attributes:
      generation_root(str): Root directory for all generated simulation input files.

    """
    def __init__(self, generation_root):
        self.generation_root = os.path.abspath(generation_root)

    def run(self, personal=False):
        '''Runs the experiments.'''
        assert os.environ.get("ARGOS_PLUGIN_PATH") is not None, ("ERROR: You must have ARGOS_PLUGIN_PATH defined")

        print("- Running all experiments...")
        try:
            # so that it can be run on non-supercomputers
            if personal:
                p = subprocess.Popen('cd {0} && parallel --no-notice < "{1}"'.format(
                    self.generation_root, self.generation_root + "/commands.txt"), shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()
                # print(stdout, stderr)
            else:
                # running on a supercomputer - specifically MSI
                subprocess.run('cd "{}" && module load parallel && sort -u $PBS_NODEFILE > unique-nodelist.txt && \
                                parallel --jobs 1 --sshloginfile unique-nodelist.txt --workdir $PWD < "{}"'.format(self.repo_dir, self.commands_file_path),
                               shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print("ERROR: Experiments failed!")
            raise e
        print("- Experiments finished!")
