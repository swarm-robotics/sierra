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
from core.variables.base_variable import BaseVariable


class Type(BaseVariable):

    """
    Defines the type of distribution of objects in the arena.

    Attributes:
        dist_type: [single_source, dual_source, quad_source, powerlaw, random].
    """

    def __init__(self, dist_type: str):
        self.dist_type = dist_type

    def gen_attr_changelist(self):
        """
        Generate a list of sets of changes necessary to make to the input file to correctly set up
        the simulation with the specified block distribution
        """
        return [set([(".//arena_map/blocks/distribution", "dist_type", "{0}".format(self.dist_type))])]

    def gen_tag_rmlist(self):
        return []

    def gen_tag_addlist(self):
        return []


class TypeSingleSource(Type):
    def __init__(self):
        super().__init__("single_source")


class TypeDualSource(Type):
    def __init__(self):
        super().__init__("dual_source")


class TypeQuadSource(Type):
    def __init__(self):
        super().__init__("quad_source")


class TypePowerLaw(Type):
    def __init__(self):
        super().__init__("powerlaw")


class TypeRandom(Type):
    def __init__(self):
        super().__init__("random")


class Quantity(BaseVariable):

    """
    Defines the # of blocks in the arena. An equal # of all block types are created (# blocks/ #
    block types).

    Attributes:
      blocks_list(list): List of block quantities to be distributed.
    """

    def __init__(self, blocks_list):
        self.blocks_list = blocks_list

    def gen_attr_changelist(self):
        """
        Generate a list of sets of changes necessary to make to the input file to correctly set up
        the simulation with the specified # blocks.
        """
        return [set([
            (".//arena_map/blocks/distribution/manifest", "n_cube", "{0}".format(int(n / 2.0))),
            (".//arena_map/blocks/distribution/manifest", "n_ramp", "{0}".format(int(n / 2.0)))]) for n in self.blocks_list]

    def gen_tag_addlist(self):
        return []

    def gen_tag_rmlist(self):
        return []