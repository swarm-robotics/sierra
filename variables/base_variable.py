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


class BaseVariable:
    def gen_attr_changelist(self):
        """Generate list of sets for changing attributes in the template input file."""
        raise NotImplementedError

    def gen_tag_rmlist(self):
        """Generate list of sets for removing tags in the template input file."""
        raise NotImplementedError

    def gen_tag_addlist(self):
        """
        Generate list of sets for adding tags (and possibly attributes) in the template input
        file.
        """
        raise NotImplementedError

    def gen_exp_dirnames(self):
        """
        Generate list of strings from the current changelist to use for directory names within a
        batched experiment.
        """
        raise NotImplementedError
