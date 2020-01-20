# Copyright 2018 John Harwell, All rights reserved.
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
#
"""
Definition:
    CD{density}.I{Arena Size Increment}

    - density - <integer>p<integer> (i.e. 5p0 for 5.0)

    - Arena Size Increment - Size in meters that the X and Y dimensions should increase by in
                             between experiments. Larger values here will result in larger arenas
                             and more blocks. Must be an integer.

Examples:
    - ``CD1p0.I16``: Constant density of 1.0. Arena dimensions will increase by 16 in both X and Y
                     for each experiment in the batch.

"""

import typing as tp
import os

from core.variables import constant_density as cd
import core.generators.scenario_generator_parser as sgp
import core.utils


class BlockConstantDensity(cd.ConstantDensity):
    """
    A univariate range specifiying the block density (ratio of block count to arena size) to hold
    constant as arena size is increased. This class is a base class which should (almost)
    never be used on its own. Instead, the ``factory()`` function should be used to dynamically
    create derived classes expressing the user's desired density.
    """

    # How many experiments to run for the given density value, in which the arena size is increased
    # from its initial value according to parsed parameters.
    kExperimentsPerDensity = 4

    def __init__(self,
                 cli_arg: str,
                 main_config: tp.Dict[str, str],
                 batch_generation_root: str,
                 target_density: float,
                 dimensions: tp.List[tuple],
                 dist_type: str):
        cd.ConstantDensity.__init__(self,
                                    cli_arg,
                                    main_config,
                                    batch_generation_root,
                                    target_density,
                                    dimensions,
                                    dist_type)

    def gen_attr_changelist(self) -> list:
        """
        Generate list of sets of changes to input file to set the # blocks for a set of arena
        sizes such that the blocks density is constant. Blocks are approximated as point masses.
        """
        for changeset in self.changes:
            for c in changeset:
                if c[0] == ".//arena" and c[1] == "size":
                    x, y, z = c[2].split(',')
                    n_blocks = max(1, (int(x) * int(y)) * (self.target_density / 100.0))
                    changeset.add((".//arena_map/blocks/distribution/manifest",
                                   "n_cube", "{0}".format(int(n_blocks / 2.0))))
                    changeset.add((".//arena_map/blocks/distribution/manifest",
                                   "n_ramp", "{0}".format(int(n_blocks / 2.0))))
                    break

        return self.changes

    def gen_exp_dirnames(self, cmdopts: tp.Dict[str, str]) -> tp.List[str]:
        changes = self.gen_attr_changelist()
        density = self.def_str.split('.')[1]
        dirs = []
        for chg in changes:
            n_blocks = 0
            for path, attr, value in chg:
                if 'n_cube' in attr or 'n_ramp' in attr:
                    n_blocks += int(value)

            dirs.append(density + '+bc' + str(n_blocks))
        if not cmdopts['named_exp_dirs']:
            return ['exp' + str(x) for x in range(0, len(dirs))]
        else:
            return dirs

    def graph_xticks(self, cmdopts: tp.Dict[str, str], exp_dirs) -> tp.List[float]:
        if exp_dirs is not None:
            dirs = exp_dirs
        else:
            dirs = self.gen_exp_dirnames(cmdopts)

        areas = []
        for d in dirs:
            pickle_fpath = os.path.join(self.batch_generation_root,
                                        d,
                                        "exp_def.pkl")
            exp_def = core.utils.unpickle_exp_def(pickle_fpath)
            for e in exp_def:
                if e[0] == ".//arena" and e[1] == "size":
                    x, y, z = e[2].split(",")
                    areas.append(int(x) * int(y))
        return areas

    def graph_xticklabels(self, cmdopts: tp.Dict[str, str], exp_dirs) -> tp.List[float]:
        return [str(x) + r' $m^2$' for x in self.graph_xticks(cmdopts, exp_dirs)]

    def graph_xlabel(self, cmdopts: tp.Dict[str, str]) -> str:
        return r"Block Density ({0}\%)".format(self.target_density)

    def pm_query(self, pm) -> bool:
        return pm in ['blocks-collected']


def factory(cli_arg: str, main_config:
            tp.Dict[str, str],
            batch_generation_root: str,
            **kwargs):
    """
    factory to create ``BlockConstantDensity`` derived classes from the command line definition of
    batch criteria.

    """
    attr = cd.ConstantDensityParser().parse(cli_arg)
    kw = sgp.ScenarioGeneratorParser.reparse_str(kwargs['scenario'])

    if kw['dist_type'] == "SS" or kw['dist_type'] == "DS":
        dims = [(x, int(x / 2)) for x in range(kw['arena_x'],
                                               kw['arena_x'] +
                                               BlockConstantDensity.kExperimentsPerDensity *
                                               attr['arena_size_inc'],
                                               attr['arena_size_inc'])]
    elif kw['dist_type'] == "PL" or kw['dist_type'] == "RN":
        dims = [(x, x) for x in range(kw['arena_x'],
                                      kw['arena_x'] +
                                      BlockConstantDensity.kExperimentsPerDensity *
                                      attr['arena_size_inc'],
                                      attr['arena_size_inc'])]
    else:
        raise NotImplementedError(
            "Unsupported block dstribution '{0}': Only SS,DS,QS,RN supported".format(kw['dist_type']))

    def __init__(self):
        BlockConstantDensity.__init__(self,
                                      cli_arg,
                                      main_config,
                                      batch_generation_root,
                                      attr["target_density"],
                                      dims,
                                      kw['dist_type'])

    return type(cli_arg,
                (BlockConstantDensity,),
                {"__init__": __init__})