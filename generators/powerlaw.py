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
import variables as ev
import pickle


class PLGenerator(ExpInputGenerator):

    """
    Modifies simulation input file template for powerlaw foraging:

    - Square arena
    - Powerlaw block distribution
    - # robots unspecified
    - # blocks unspecified

    Attributes:
      dimension(int): dimensions of the square arena.
    """

    def __init__(self, template_config_file, generation_root, exp_output_root,
                 exp_def_fname, sim_opts, controller):
        super().__init__(template_config_file, generation_root, exp_output_root,
                         exp_def_fname, sim_opts)

    def generate(self, xml_luigi):
        arena_dim = self.sim_opts["arena_dim"]
        shape = ev.arena_shape.SquareArena(sqrange=[arena_dim[0]])
        [xml_luigi.attribute_change(a[0], a[1], a[2]) for a in shape.gen_attr_changelist()[0]]

        # Write arena dimension info to file for later retrieval
        with open(self.exp_def_fpath, 'ab') as f:
            pickle.dump(shape.gen_attr_changelist()[0], f)

        rms = shape.gen_tag_rmlist()
        if len(rms):
            [xml_luigi.tag_remove(a) for a in rms[0]]

        source = ev.block_distribution.TypePowerLaw()
        [xml_luigi.attribute_change(a[0], a[1], a[2]) for a in source.gen_attr_changelist()[0]]
        rms = source.gen_tag_rmlist()
        if len(rms):
            [xml_luigi.tag_remove(a) for a in rms[0]]

        nest_pose = ev.nest_pose.NestPose("powerlaw", [(arena_dim[0], arena_dim[0])])
        [xml_luigi.attribute_change(a[0], a[1], a[2]) for a in nest_pose.gen_attr_changelist()[0]]
        rms = nest_pose.gen_tag_rmlist()

        if len(rms):
            [xml_luigi.tag_remove(a[0], a[1]) for a in rms[0]]

        # Configure physics engines. Cannot be done in the parent class, as that is for BOTH
        # controller and scenario generation, and the arena dimensions are None for configuring
        # controllers.
        engines = ev.physics_engines.PhysicsEngines(self.sim_opts["n_physics_engines"],
                                                    "uniform_grid",
                                                    arena_dim)

        for a in engines.gen_tag_rmlist()[0]:
            xml_luigi.tag_remove(a[0], a[1])

        for a in engines.gen_tag_addlist()[0]:
            xml_luigi.tag_add(a[0], a[1], a[2])

        self._create_all_sim_inputs(self._generate_random_seeds(), xml_luigi)
