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

import implements


class IBaseVariable(implements.Interface):
    def gen_attr_changelist(self) -> list:
        """Generate list of sets for changing attributes in the template input file."""

    def gen_tag_rmlist(self) -> list:
        """Generate list of sets for removing tags in the template input file."""

    def gen_tag_addlist(self) -> list:
        """
        Generate list of sets for adding tags (and possibly attributes) in the template input
        file.
        """


__api__ = [
    'IBaseVariable'
]
