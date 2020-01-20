# Copyright 2019 John Harwell, All rights reserved.
#
#  This file is part of SIERRA.
#
#  SIERRA is free software: you can redistribute it and/or modify it under the
#  terms of the GNU General Public License as published by the Free Software
#  Foundation, either version 3 of the License, or (at your option) any later
#  version.
#
#  SIERRA is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
#  A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  SIERRA.  If not, see <http://www.gnu.org/licenses/
"""
Definition:
    All[.Z{population}]

    population - The swarm size to use (optional)

Examples:
    - ``All.Z16``: All possible task allocation policies with swarms of size 16.
    - ``All``: All possible task allocation policies; swarm size not modified.
"""


import re
import typing as tp

from core.variables.batch_criteria import UnivarBatchCriteria
from core.variables.population import Population


class TAPolicySet(UnivarBatchCriteria):
    """
    A univariate range specifiying the set of task allocation policies (and possibly swarm size) to
    use to define the batched experiment. This class is a base class which should (almost) never be
    used on its own. Instead, the ``factory()`` function should be used to dynamically create
    derived classes expressing the user's desired policies and swarm size.

    Attributes:
        policies: List of policies to enable for a specific simulation.
        population: Swarm size to use for a specific simulation.
    """
    kPolicies = ['random', 'stoch_nbhd1', 'strict_greedy', 'epsilon_greedy', 'UCB1']

    def __init__(self, cli_arg: str,
                 main_config: tp.Dict[str, str],
                 batch_generation_root: str,
                 policies: list,
                 population: int):
        UnivarBatchCriteria.__init__(self, cli_arg, main_config, batch_generation_root)
        self.policies = policies
        self.population = population

    def gen_attr_changelist(self) -> list:
        # Swarm size is optional. It can be (1) controlled via this variable, (2) controlled by
        # another variable in a bivariate batch criteria, (3) not controlled at all. For (2), (3),
        # the swarm size can be None.
        if self.population is not None:
            size_attr = [next(iter(Population(self.cli_arg,
                                             self.main_config,
                                             self.batch_generation_root,
                                             [self.population]).gen_attr_changelist()[0]))]
        else:
            size_attr = []
        changes = []

        for p in self.policies:
            c = []
            c.extend(size_attr)
            c.extend([(".//task_alloc", "policy", "{0}".format(p))])

            changes.append(set(c))
        return changes

    def gen_exp_dirnames(self, cmdopts: tp.Dict[str, str]) -> tp.List[str]:
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

    def graph_xticks(self, cmdopts: tp.Dict[str, str], exp_dirs: tp.List[str]) -> tp.List[float]:
        if exp_dirs is not None:
            dirs = exp_dirs
        else:
            dirs = self.gen_exp_dirnames(cmdopts)

        return [i for i in range(1, len(dirs) + 1)]

    def graph_xticklabels(self, cmdopts: tp.Dict[str, str], exp_dirs) -> tp.List[float]:
        return ['Random', 'STOCH-N1', 'MAT-OPT', r'$\epsilon$-greedy', 'UCB1']

    def graph_xlabel(self, cmdopts: tp.Dict[str, str]) -> str:
        return "Task Allocation Policy"

    def pm_query(self, query: str) -> bool:
        return query in ['blocks-collected']


class TAPolicySetParser():
    """
    Enforces the cmdline definition of the criteria described in the module docstring.
    """

    def parse(self, criteria_str: str):
        """
        Returns:
            Dictionary with keys:
                population: Swarm size to use (optional)

        """
        ret = {}

        # Parse task allocation policy set
        assert 'All' in criteria_str, \
            "FATAL: Bad TAPolicy set in criteria '{0}'. Must be 'All'".format(criteria_str)

        # Parse swarm size
        res = re.search("\.Z[0-9]+", criteria_str)
        if res is not None:
            ret['population'] = int(res.group(0)[2:])

        return ret


def factory(cli_arg: str,
            main_config: tp.Dict[str, str],
            batch_generation_root: str,
            **kwargs):
    """
    Factory to create :class:`TAPolicySet` derived classes from the command line definition of batch
    criteria.

    """
    attr = TAPolicySetParser().parse(cli_arg)

    def __init__(self):
        TAPolicySet.__init__(self, cli_arg, main_config, batch_generation_root,
                             TAPolicySet.kPolicies, attr.get('population', None))

    return type(cli_arg,
                (TAPolicySet,),
                {"__init__": __init__})