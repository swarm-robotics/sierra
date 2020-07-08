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
Classes for the flexibility batch criteria. See :ref:`ln-bc-flexibility` for usage documentation.

"""

import math
import typing as tp

from core.variables.batch_criteria import UnivarBatchCriteria
from core.variables.population_size import PopulationSize
from core.perf_measures import vcs
from core.variables.flexibility_parser import FlexibilityParser


class Flexibility(UnivarBatchCriteria):
    """
    A univariate range specifiying the set of temporal variances (and possibly swarm size) to
    use to define the batched experiment. This class is a base class which should (almost) never be
    used on its own. Instead, the ``factory()`` function should be used to dynamically create
    derived classes expressing the user's desired variance set.

    Attributes:
        variances: List of tuples specifying the waveform characteristics for each type of
                   applied variance. Cardinality of each tuple is 3, and defined as follows:

                   - xml parent path: The path to the parent element in the XML tree.
                   - [type, frequency, amplitude, offset, phase]: Waveform parameters.
                   - value: Waveform specific parameters (optional, will be None if not used for the
                            selected variance)
    """

    def __init__(self,
                 cli_arg: str,
                 main_config: tp.Dict[str, str],
                 batch_generation_root: str,
                 variances: list,
                 population: int) -> None:
        UnivarBatchCriteria.__init__(self, cli_arg, main_config, batch_generation_root)

        self.variances = variances
        self.population = population

    def gen_attr_changelist(self) -> list:
        """
        Generate a list of sets of changes necessary to make to the input file to correctly set up
        the simulation with the specified temporal variances.
        """
        all_changes = [set([("{0}/waveform".format(v[0]), "type", str(v[1])),
                            ("{0}/waveform".format(v[0]), "frequency", str(v[2])),
                            ("{0}/waveform".format(v[0]), "amplitude", str(v[3])),
                            ("{0}/waveform".format(v[0]), "offset", str(v[4])),
                            ("{0}/waveform".format(v[0]), "phase", str(v[5]))]) for v in self.variances]

        # Swarm size is optional. It can be (1) controlled via this variable, (2) controlled by
        # another variable in a bivariate batch criteria, (3) not controlled at all. For (2), (3),
        # the swarm size can be None.
        if self.population is not None:
            size_chgs = PopulationSize(self.cli_arg,
                                       self.main_config,
                                       self.batch_generation_root,
                                       [self.population]).gen_attr_changelist()[0]
            for exp_chgs in all_changes:
                exp_chgs |= size_chgs

        return all_changes

    def graph_xticks(self,
                     cmdopts: tp.Dict[str, str],
                     exp_dirs: tp.List[str] = None) -> tp.List[float]:

        # If exp_dirs is passed, then we have been handed a subset of the total # of directories in
        # the batch exp root, and so n_exp() will return more experiments than we actually
        # have. This behavior is needed to correct extract x/y values for bivar experiments.
        if exp_dirs is not None:
            m = len(exp_dirs)
        else:
            m = self.n_exp()

        # zeroth element is the distance to ideal conditions for exp0, which is by definition ideal
        # conditions, so the distance is 0.
        ret = [0.0]
        ret.extend([vcs.EnvironmentalCS(self.main_config, cmdopts, x)(self, exp_dirs)
                    for x in range(1, m)])
        return ret

    def graph_xticklabels(self,
                          cmdopts: tp.Dict[str, str],
                          exp_dirs: tp.List[str] = None) -> tp.List[str]:
        return list(map(str, self.graph_xticks(cmdopts, exp_dirs)))

    def graph_xlabel(self, cmdopts: tp.Dict[str, str]) -> str:
        return vcs.method_xlabel(cmdopts["envc_cs_method"])

    def gen_exp_dirnames(self, cmdopts: tp.Dict[str, str]) -> tp.List[str]:
        return ['exp' + str(x) for x in range(0, len(self.gen_attr_changelist()))]

    def pm_query(self, pm: str) -> bool:
        return pm in ['blocks-transported', 'reactivity', 'adaptability']


def factory(cli_arg: str, main_config: dict, batch_generation_root: str, **kwargs):
    """
    Factory to create :class:`Flexibility` derived classes from the command line definition of
    batch criteria.

    """
    attr = FlexibilityParser()(cli_arg)

    def gen_variances(attr: dict):

        amps = main_config['sierra']['flexibility'][attr['variance_type'] + '_amp']
        hzs = main_config['sierra']['flexibility']['hz']

        # All variances need to have baseline/ideal conditions for comparison, which is a small
        # constant penalty
        variances = [(attr["xml_parent_path"],
                      "Constant",
                      hzs[0],
                      amps[0],
                      0.0,
                      0.0)]

        if any(v == attr["waveform_type"] for v in ["Sine", "Square", "Sawtooth"]):
            variances.extend([(attr["xml_parent_path"],
                               attr["waveform_type"],
                               1.0 / hz,
                               amp,
                               amp,
                               0) for hz in hzs[1:] for amp in amps[1:]])
        elif attr["waveform_type"] == "StepD":
            variances.extend([(attr["xml_parent_path"],
                               "Square",
                               1 / (2 * attr["waveform_param"]),
                               amp,
                               0,
                               0) for amp in amps[1:]])

        if attr["waveform_type"] == "StepU":
            variances.extend([(attr["xml_parent_path"],
                               "Square",
                               1 / (2 * attr["waveform_param"]),
                               amp,
                               amp,
                               math.pi) for amp in amps[1:]])
        return variances

    def __init__(self) -> None:
        Flexibility.__init__(self,
                             cli_arg,
                             main_config,
                             batch_generation_root,
                             gen_variances(attr),
                             attr.get("population", None))

    return type(cli_arg,
                (Flexibility,),
                {"__init__": __init__})


__api__ = [
    'Flexibility'
]
