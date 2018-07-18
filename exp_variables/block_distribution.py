"""
 Copyright 2018 John Harwell, All rights reserved.

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

from exp_variables.base_variable import BaseVariable


class Type(BaseVariable):

    """
    Defines the distribution of objects in the arena.

    Attributes:
      dist_type(str): [single_source, dual_source, powerlaw, random].
    """

    def __init__(self, dist_type):
        self.dist_type = dist_type

    def gen_attr_changelist(self):
        """
        Generate a list of sets of changes necessary to make to the input file to correctly set up
        the simulation with the specified block distribution
        """
        return [set([("block_distribution.dist_type", "{0}".format(self.dist_type))])]

    def gen_tag_rmlist(self):
        return []


class TypeSingleSource(Type):
    def __init__(self):
        super().__init__("single_source")


class TypeDualSource(Type):
    def __init__(self):
        super().__init__("dual_source")


class TypePowerLaw(Type):
    def __init__(self):
        super().__init__("powerlaw")


class TypeRandom(Type):
    def __init__(self):
        super().__init__("random")


class Quantity(BaseVariable):

    """
    Defines the # of blocks in the arena.

    Attributes:
      blocks_list(list): List of block quantities to be distributed.
    """

    def __init__(self, blocks_list):
        self.blocks_list = blocks_list

    def gen_list(self):
        """
        Generate a list of sets of changes necessary to make to the input file to correctly set up
        the simulation with the specified # blocks.
        """
        return [set([("block_distribution.n_blocks", "{0}".format(n)) for n in self.blocks_list])]


class QuantityLog64(Quantity):
    def __init__(self):
        super().__init__([x ** 2 for x in range(2, 7)])


class QuantityLog128(Quantity):
    def __init__(self):
        super().__init__([x ** 2 for x in range(2, 8)])


class QuantityLog256(Quantity):
    def __init__(self):
        super().__init__([x ** 2 for x in range(2, 9)])


class QuantityLog512(Quantity):
    def __init__(self):
        super().__init__([x ** 2 for x in range(2, 10)])


class QuantityLog1024(Quantity):
    def __init__(self):
        super().__init__([x ** 2 for x in range(2, 11)])
