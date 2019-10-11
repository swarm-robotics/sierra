"""
 Copyright 2019 John Harwell, All rights reserved.

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

from variables.batch_criteria import UnivarBatchCriteria
from variables.ta_policy_set_parser import TAPolicySetParser
from variables.swarm_size import SwarmSize


class TAPolicySet(UnivarBatchCriteria):
    """
    Defines the task allocation policy to use during simulation.

    Attributes:
      policies(list): List of policies to enable for a specific simulation.
      swarm_size(str): Swarm size to use for a specific simulation.
    """

    def __init__(self, cmdline_str, main_config, batch_generation_root, policies, swarm_size):
        UnivarBatchCriteria.__init__(self, cmdline_str, main_config, batch_generation_root)
        self.policies = policies
        self.swarm_size = swarm_size

    def gen_attr_changelist(self):
        # Swarm size is optional. It can be (1) controlled via this variable, (2) controlled by
        # another variable in a bivariate batch criteria, (3) not controlled at all. For (2), (3),
        # the swarm size can be None.
        if self.swarm_size is not None:
            size_attr = [next(iter(SwarmSize(self.cmdline_str,
                                             self.main_config,
                                             self.batch_generation_root,
                                             [self.swarm_size]).gen_attr_changelist()[0]))]
        else:
            size_attr = []
        changes = []

        for p in self.policies:
            c = []
            c.extend(size_attr)
            c.extend([(".//task_alloc", "policy", "{0}".format(p))])

            changes.append(set(c))
        return changes

    def gen_exp_dirnames(self, cmdopts):
        changes = self.gen_attr_changelist()
        dirs = []
        for chgset in changes:
            policy = None
            size = ''
            for path, attr, value in chgset:
                if 'policy' in attr:
                    policy = value
                if 'quantity' in attr:
                    size = 'size' + value

            dirs.append(policy + '|' * (size != '') + size)

        if not cmdopts['named_exp_dirs']:
            return ['exp' + str(x) for x in range(0, len(dirs))]
        else:
            return dirs

    def sc_graph_labels(self, scenarios):
        return [s[-5:-2].replace('p', '.') for s in scenarios]

    def sc_sort_scenarios(self, scenarios):
        return sorted(scenarios,
                      key=lambda s: float(s.split('-')[2].split('.')[0][0:3].replace('p', '.')))

    def graph_xvals(self, cmdopts, exp_dirs):
        return [i for i in range(1, self.n_exp() + 1)]

    def graph_xlabel(self, cmdopts):
        return "Task Allocation Policy"

    def pm_query(self, query):
        return query in ['blocks-collected']


def Factory(cmdline_str, main_config, batch_generation_root, **kwargs):
    """
    Creates TAPolicySet classes from the command line definition.
    """
    attr = TAPolicySetParser().parse(cmdline_str)

    def gen_policies():
        return ['random', 'stoch_greedy_nbhd', 'strict_greedy', 'epsilon_greedy']

    def __init__(self):
        TAPolicySet.__init__(self, cmdline_str, main_config, batch_generation_root,
                             gen_policies(), attr.get('swarm_size', None))

    return type(cmdline_str,
                (TAPolicySet,),
                {"__init__": __init__})