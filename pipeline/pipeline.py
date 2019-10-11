"""
 Copyright 2018 London Lowmanstone, John Harwell, All rights reserved.

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

from pipeline.stage1 import PipelineStage1
from pipeline.stage2 import PipelineStage2
from pipeline.stage3 import PipelineStage3
from pipeline.stage4 import PipelineStage4
from pipeline.stage5 import PipelineStage5


class Pipeline:

    """
    Automation for running ARGoS robotic simulation experiments in parallel

    Implements the following pipeline for single OR batched experiments:

    1. Generate a set of XML configuration files from a template suitable for
       input into ARGoS that contain user-specified modifications.
    2. Run the specified  # of experiments in parallel using GNU Parallel on
       the provided set of hosts on MSI (or on a single personal computer for testing).
    3. Average the .csv results of the simulation runs together.
    4. Generate a user-defined set of graphs based on the averaged results for each
       experiment, and possibly across experiments for batches.
    5. Compare controllers that have been tested with the same experiment batch across different
       performance measures.
    """

    def __init__(self, args, input_generator, batch_criteria):
        self.args = args
        self.cmdopts = {
            # general
            'output_root': self.args.output_root,
            'graph_root': self.args.graph_root,
            'sierra_root': self.args.sierra_root,
            'generation_root': self.args.generation_root,
            'controller': self.args.controller,
            'scenario': self.args.scenario,
            'template_config_file': self.args.template_config_file,
            'config_root': self.args.config_root,
            'named_exp_dirs': self.args.named_exp_dirs,

            # stage 1
            'time_setup': self.args.time_setup,
            'n_physics_engines': self.args.n_physics_engines,

            # stage 2
            'exec_exp_range': self.args.exec_exp_range,
            'exec_method': self.args.exec_method,
            'n_threads': self.args.n_threads,
            'n_sims': self.args.n_sims,
            'exec_resume': self.args.exec_resume,
            'with_rendering': self.args.with_rendering,

            # stage 3
            'no_verify_results': self.args.no_verify_results,
            'gen_stddev': self.args.gen_stddev,
            'results_process_tasks': self.args.results_process_tasks,
            'render_cmd_opts': self.args.render_cmd_opts,
            'render_cmd_ofile': self.args.render_cmd_ofile,

            # stage 4
            'envc_cs_method': self.args.envc_cs_method,
            'with_hists': self.args.with_hists,
            'gen_vc_plots': self.args.gen_vc_plots,
            'plot_log_xaxis': self.args.plot_log_xaxis,
            'reactivity_cs_method': self.args.reactivity_cs_method,
            'adaptability_cs_method': self.args.adaptability_cs_method,
            'exp_graphs': self.args.exp_graphs,
            'n_blocks': self.args.n_blocks
        }
        self.input_generator = input_generator
        self.batch_criteria = batch_criteria

    def run(self):

        if 1 in self.args.pipeline:
            self.__generate_inputs()

        if 2 in self.args.pipeline:
            self.__run_experiments()

        if 3 in self.args.pipeline:
            self.__process_results()

        if 4 in self.args.pipeline:
            self.__intra_batch_graphs()

        # not part of default pipeline
        if 5 in self.args.pipeline:
            self.__inter_batch_graphs()

    # Private functions
    def __generate_inputs(self):
        PipelineStage1().run(self.cmdopts,
                             self.input_generator)

    def __run_experiments(self):
        PipelineStage2().run(self.cmdopts, self.batch_criteria)

    def __process_results(self):
        PipelineStage3(self.cmdopts).run()

    def __intra_batch_graphs(self):
        PipelineStage4(self.cmdopts).run(self.batch_criteria)

    def __inter_batch_graphs(self):
        PipelineStage5(self.cmdopts, self.args.inter_batch_controllers).run()