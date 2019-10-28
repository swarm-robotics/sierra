# Copyright 2018 London Lowmanstone, John Harwell, All rights reserved.
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
Container module for the 5 pipeline stages implemented by SIERRA:

#. Generate a set of XML configuration files from a template suitable for
   input into ARGoS that contain user-specified modifications.
#. Run the specified  # of experiments in parallel using GNU Parallel on
   the provided set of hosts on MSI (or on a single personal computer for testing).
#. Average the .csv results of the simulation runs together.
#. Generate a user-defined set of graphs based on the averaged results for each
   experiment, and possibly across experiments for batches.
#. Compare controllers that have been tested with the same experiment batch across different
   performance measures.
"""
import typing as tp
from pipeline.stage1 import PipelineStage1
from pipeline.stage2 import PipelineStage2
from pipeline.stage3 import PipelineStage3
from pipeline.stage4 import PipelineStage4
from pipeline.stage5 import PipelineStage5


class Pipeline:
    "Implements SIERRA's 5 stage pipeline."

    def __init__(self, args, input_generator, batch_criteria, cmdopts: tp.Dict[str, str]):
        self.args = args
        self.cmdopts = {
            # general
            'sierra_root': self.args.sierra_root,
            'controller': self.args.controller,
            'scenario': self.args.scenario,
            'template_input_file': self.args.template_input_file,
            'config_root': self.args.config_root,
            'named_exp_dirs': self.args.named_exp_dirs,

            # stage 1
            'time_setup': self.args.time_setup,
            'physics_n_engines': self.args.physics_n_engines,

            # stage 2
            'exec_exp_range': self.args.exec_exp_range,
            'exec_method': self.args.exec_method,
            'n_threads': self.args.n_threads,
            'n_sims': self.args.n_sims,
            'exec_resume': self.args.exec_resume,
            'with_rendering': self.args.with_rendering,
            'hpc_env': self.args.hpc_env,

            # stage 3
            'no_verify_results': self.args.no_verify_results,
            'gen_stddev': self.args.gen_stddev,
            'results_process_tasks': self.args.results_process_tasks,
            'render_cmd_opts': self.args.render_cmd_opts,
            'render_cmd_ofile': self.args.render_cmd_ofile,

            # stage 4
            'envc_cs_method': self.args.envc_cs_method,
            'gen_vc_plots': self.args.gen_vc_plots,
            'plot_log_xaxis': self.args.plot_log_xaxis,
            'reactivity_cs_method': self.args.reactivity_cs_method,
            'adaptability_cs_method': self.args.adaptability_cs_method,
            'exp_graphs': self.args.exp_graphs,
            'n_blocks': self.args.n_blocks,

            # stage 5
            'controller_comp_list': self.args.controller_comp_list,
            'normalize_comparisons': self.args.normalize_comparisons
        }
        if cmdopts is not None:
            self.cmdopts.update(cmdopts)

        self.input_generator = input_generator
        self.batch_criteria = batch_criteria

    def run(self):
        """
        Run pipeline stages as configured.
        """
        if 1 in self.args.pipeline:
            PipelineStage1().run(self.cmdopts,
                                 self.input_generator)

        if 2 in self.args.pipeline:
            PipelineStage2().run(self.cmdopts, self.batch_criteria)

        if 3 in self.args.pipeline:
            PipelineStage3(self.cmdopts).run()

        if 4 in self.args.pipeline:
            PipelineStage4(self.cmdopts).run(self.batch_criteria)

        # not part of default pipeline
        if 5 in self.args.pipeline:
            PipelineStage5(self.cmdopts).run(self.args)
