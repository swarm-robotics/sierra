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


class NestPose(BaseVariable):

    """
    Defines the position/size of the nest based on block distribution type.

    Attributes:
      dist_type(str): The block distribution type.
      dimensions(list): List (X,Y) dimensions to generate nest poses for.
    """

    def __init__(self, dist_type, dimensions):
        self.dist_type = dist_type
        self.dimensions = dimensions

    def gen_attr_changelist(self):
        """
        Generate list of sets of changes necessary to make to the input file to correctly set up the
        simulation for the specified block distribution/nest.

        """
        if self.dist_type == "single_source":
            return [set([
                ("arena.light1.position", "2, {0}, 1.0".format(s[1] * 0.25)),
                ("arena.light1.position", "2, {0}, 1.0".format(s[1] * 0.5)),
                ("arena.light1.position", "2, {0}, 1.0".format(s[1] * 0.75)),
                ("arena_map.nest.size", "{0}, {1}".format(s[0] / 10.0, s[1] * 0.8)),
                ("arena_map.nest.center", "2.0, {0}".format(s[1] / 2.0)),
                ("fsm.nest", "2.0, {0}".format(s[1] / 2.0))
            ])
                for s in self.dimensions]
        elif self.dist_type == "powerlaw":
            return [set([
                ("arena.light1.position", "{0}, {0}, 1.0".format(s[1] * 0.5)),
                ("arena_map.nest.size", "{0}, {1}".format(s[0] / 10.0, s[0] / 10.0)),
                ("arena_map.nest.center", "{0}, {0}".format(s[0] * 0.5)),
                ("fsm.nest", "{0}, {0}".format(s[0] * 0.5))
            ])
                for s in self.dimensions]
        else:
            # Eventually, I'll want to have definitions for the other block distribution types
            raise NotImplementedError

    def gen_tag_rmlist(self):
        if self.dist_type == "single_source":
            return []
        elif self.dist_type == "powerlaw":
            return [set(["arena.light2", "arena.light3"])]
