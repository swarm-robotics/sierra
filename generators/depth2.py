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

from generators.exp_input_generator import ExpInputGenerator


class BaseGenerator(ExpInputGenerator):
    """
    Generates simulation input changes needed for all depth2 controllers.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self):
        """
        Generates all changes to the input file for the simulation (does not save):
        """
        xml_luigi = super().generate_common_defs()
        xml_luigi.attribute_change(".//loop_functions", "label", "depth2_loop_functions")
        return xml_luigi


class GRP_DPOGenerator(BaseGenerator):
    """
    Generates simulation input changes common needed for all GRP_DPO controllers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self):
        """
        Generates all changes to the input file for the simulation (does not save):
        """
        xml_luigi = super().generate()
        xml_luigi.tag_change(".//controllers", "__template__", "grp_dpo_controller")
        return xml_luigi


class GRP_MDPOGenerator(BaseGenerator):
    """
    Generates simulation input changes common needed for all GRP_MDPO controllers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self):
        """
        Generates all changes to the input file for the simulation (does not save):
        """
        xml_luigi = super().generate()
        xml_luigi.tag_change(".//controllers", "__template__", "grp_mdpo_controller")
        return xml_luigi


class OGRP_DPOGenerator(BaseGenerator):
    """
    Generates simulation input changes common needed for all OGRP_DPO controllers.
    Enables the oracle itself in the loop functions, but does not specify what elements of it are to
    be used; that is left to either manual template configuration or to batch criteria.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self):
        """
        Generates all changes to the input file for the simulation (does not save):
        """
        xml_luigi = super().generate()
        xml_luigi.tag_change(".//controllers", "__template__", "ogrp_dpo_controller")
        xml_luigi.attribute_change(".//loop_functions/oracle", "enabled", "true")
        return xml_luigi


class OGRP_MDPOGenerator(BaseGenerator):
    """
    Generates simulation input changes common needed for all OGRP_MDPO controllers.
    Enables the oracle itself in the loop functions, but does not specify what elements of it are to
    be used; that is left to either manual template configuration or to batch criteria.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self):
        """
        Generates all changes to the input file for the simulation (does not save):
        """
        xml_luigi = super().generate()
        xml_luigi.tag_change(".//controllers", "__template__", "ogrp_mdpo_controller")
        xml_luigi.attribute_change(".//loop_functions/oracle", "enabled", "true")
        return xml_luigi
