# Copyright 2019 John Harwell, All rights reserved.
#
# This file is part of SIERRA.
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
Classes for handling univariate comparisons for a single controller across a set of scenarios for
stage5 of the experimental pipeline.
"""

# Core packages
import os
import copy
import logging
import glob
import re
import typing as tp
import argparse

# 3rd party packages
import pandas as pd

# Project packages
from core.graphs.batch_ranged_graph import BatchRangedGraph
from core.graphs.stacked_surface_graph import StackedSurfaceGraph
from core.graphs.heatmap import Heatmap, DualHeatmap
from core.variables import batch_criteria as bc
import core.root_dirpath_generator as rdg
import core.generators.scenario_generator_parser as sgp
import core.utils
import core.config


class UnivarInterScenarioComparator:
    """
    Compares a single controller on different performance measures across a set of scenarios using
    univariate batch criteria, one at a time. Graph generation is controlled via a config file
    parsed in :class:`~core.pipeline.stage5.pipeline_stage5.PipelineStage5`. Univariate batch
    criteria only.

    Attributes:
        controller: Controller to use.
        scenarios: List of scenario names to compare ``controller`` across.
        sc_csv_root: Absolute directory path to the location scenario ``.csv`` files should be
                     output to.
        sc_graph_root: Absolute directory path to the location the generated graphs should be output
                       to.
        cmdopts: Dictionary of parsed cmdline parameters.
        cli_args: :class:`argparse` object containing the cmdline parameters. Needed for
                  :class:`~core.variables.batch_criteria.BatchCriteria` generation for each scenario
                  controllers are compared within, as batch criteria is dependent on
                  controller+scenario definition, and needs to be re-generated for each scenario in
                  order to get graph labels/axis ticks to come out right in all cases.

    """

    def __init__(self,
                 controller: str,
                 scenarios: tp.List[str],
                 roots: tp.Dict[str, str],
                 cmdopts: dict,
                 cli_args,
                 main_config: dict) -> None:
        self.controller = controller
        self.scenarios = scenarios
        self.sc_graph_root = roots['sc_graphs']
        self.sc_csv_root = roots['sc_csvs']
        self.sc_model_root = roots['sc_models']

        self.cmdopts = cmdopts
        self.cli_args = cli_args
        self.main_config = main_config
        self.logger = logging.getLogger(__name__)

    def __call__(self, graphs: dict, legend: tp.List[str]) -> None:
        # Obtain the list of simulation results directories to draw from.
        batch_leaves = os.listdir(os.path.join(self.cmdopts['sierra_root'],
                                               self.cmdopts['project'],
                                               self.controller))

        # The FS gives us batch leaves which might not be in the same order as the list of specified
        # scenarios, so we:
        #
        # 1. Remove all batch leaves which do not have a counterpart in the scenario list we are
        #    comparing across.
        # 2. Do matching to get the indices of the batch leaves relative to the list, and then sort
        #    it.
        batch_leaves = [leaf for leaf in batch_leaves for s in self.scenarios if s in leaf]
        indices = [self.scenarios.index(s)
                   for leaf in batch_leaves for s in self.scenarios if s in leaf]
        batch_leaves = [leaf for s, leaf in sorted(zip(indices, batch_leaves),
                                                   key=lambda pair: pair[0])]

        # For each controller comparison graph we are interested in, generate it using data from all
        # scenarios
        cmdopts = copy.deepcopy(self.cmdopts)
        for graph in graphs:
            for leaf in batch_leaves:
                if self._leaf_select(leaf):
                    self._compare_across_scenarios(cmdopts=cmdopts,
                                                   graph=graph,
                                                   batch_leaf=leaf,
                                                   legend=legend)
                else:
                    self.logger.debug("Skipping '%s': not in scenario list %s/does not match %s",
                                      leaf,
                                      self.scenarios,
                                      self.cli_args.batch_criteria)

    def _leaf_select(self, candidate: str) -> bool:
        """Determine if a scenario that the controller has been run on in the past is part of the
        set passed that the controller should be compared across (i.e., the controller is not
        compared across all scenarios it has ever been run on).

        """,
        template_stem, scenario, _ = rdg.parse_batch_leaf(candidate)
        leaf = rdg.gen_batch_leaf(criteria=self.cli_args.batch_criteria,
                                  scenario=scenario,
                                  template_stem=template_stem)
        return leaf in candidate and scenario in self.scenarios

    def _compare_across_scenarios(self,
                                  cmdopts: dict,
                                  graph: dict,
                                  batch_leaf: str,
                                  legend: tp.List[str]) -> None:

        # We need to generate the root directory paths for each batched experiment
        # (which # lives inside of the scenario dir), because they are all
        # different. We need generate these paths for EACH controller, because the
        # controller is part of the batch root path.
        paths = rdg.regen_from_exp(sierra_rpath=self.cli_args.sierra_root,
                                   project=self.cli_args.project,
                                   batch_leaf=batch_leaf,
                                   controller=self.controller)
        cmdopts.update(paths)

        # For each scenario, we have to create the batch criteria for it, because they
        # are all different.

        criteria = bc.factory(self.main_config, cmdopts, self.cli_args, self.scenarios[0])

        self._gen_csv(cmdopts=cmdopts,
                      batch_leaf=batch_leaf,
                      src_stem=graph['src_stem'],
                      dest_stem=graph['dest_stem'])

        self._gen_graph(criteria=criteria,
                        cmdopts=cmdopts,
                        dest_stem=graph['dest_stem'],
                        title=graph['title'],
                        label=graph['label'],
                        legend=legend)

    def _gen_graph(self,
                   criteria: bc.IConcreteBatchCriteria,
                   cmdopts: dict,
                   dest_stem: str,
                   title: str,
                   label: str,
                   legend: tp.List[str]) -> None:
        """
        Generates a :class:`~core.graphs.batch_ranged_graph.BatchRangedGraph` comparing the
        specified controller across specified scenarios.
        """
        ipath_stem = os.path.join(self.sc_csv_root, dest_stem + "-" + self.controller)
        model_ipath_stem = os.path.join(self.sc_model_root, dest_stem + "-" + self.controller)
        img_opath = os.path.join(self.sc_graph_root, dest_stem) + '-' + \
            self.controller + core.config.kImageExt
        xticks = criteria.graph_xticks(cmdopts)
        xtick_labels = criteria.graph_xticklabels(cmdopts)

        BatchRangedGraph(input_fpath=ipath_stem + '.csv',
                         stddev_fpath=ipath_stem + '.stddev',
                         model_fpath=model_ipath_stem + '.model',
                         model_legend_fpath=model_ipath_stem + '.legend',
                         output_fpath=img_opath,
                         title=title,
                         xlabel=criteria.graph_xlabel(cmdopts),
                         ylabel=label,
                         xticks=xticks[criteria.inter_exp_graphs_exclude_exp0():],
                         logyscale=cmdopts['plot_log_yscale'],
                         large_text=cmdopts['plot_large_text'],
                         legend=legend).generate()

    def _gen_csv(self,
                 cmdopts: dict,
                 batch_leaf: str,
                 src_stem: str,
                 dest_stem: str) -> None:
        """
        Helper function for generating a set of .csv files for use in inter-scenario graph
        generation.

        Generates:

        - ``.csv`` file containing results for each scenario the controller is being compared
          across, 1 per line.

        - ``.stddev`` file containing stddev for the generated ``.csv`` file, 1 per line.

        - ``.model`` file containing model predictions for controller behavior during each scenario,
          1 per line (not generated if models were not run the performance measures we are
          generating graphs for).

        - ``.legend`` file containing legend values for models to plot (not generated if models were
          not run for the performance measures we are generating graphs for).
        """

        csv_ipath = os.path.join(cmdopts['batch_output_root'],
                                 self.main_config['sierra']['collate_csv_leaf'],
                                 src_stem + ".csv")
        stddev_ipath = os.path.join(cmdopts['batch_output_root'],
                                    self.main_config['sierra']['collate_csv_leaf'],
                                    src_stem + ".stddev")

        model_ipath_stem = os.path.join(cmdopts['batch_model_root'], src_stem)
        model_opath_stem = os.path.join(self.sc_model_root, dest_stem + "-" + self.controller)

        opath_stem = os.path.join(self.sc_csv_root, dest_stem + "-" + self.controller)

        # Some experiments might not generate the necessary performance measure .csvs for graph
        # generation, which is OK.
        if not core.utils.path_exists(csv_ipath):
            self.logger.warning("%s missing for controller %s", csv_ipath, self.controller)
            return

        # Collect performance measure results. Append to existing dataframe if it exists, otherwise
        # start a new one.
        data_df = self._accum_df(csv_ipath, opath_stem + '.csv', src_stem)
        core.utils.pd_csv_write(data_df, opath_stem + '.csv', index=False)

        # Collect performance results stddev. Append to existing dataframe if it exists, otherwise
        # start a new one.
        stddev_df = self._accum_df(stddev_ipath, opath_stem + '.stddev', src_stem)
        if stddev_df is not None:
            core.utils.pd_csv_write(stddev_df, opath_stem + '.stddev', index=False)

        # Collect performance results models and legends. Append to existing dataframes if they
        # exist, otherwise start new ones.
        model_df = self._accum_df(model_ipath_stem + '.model',
                                  model_opath_stem + '.model',
                                  src_stem)
        if model_df is not None:
            core.utils.pd_csv_write(model_df, model_opath_stem + '.model', index=False)
            with open(model_opath_stem + '.legend', 'a') as f:
                _, scenario, _ = rdg.parse_batch_leaf(batch_leaf)
                kw = sgp.ScenarioGeneratorParser.reparse_str(scenario)
                f.write("{0} Prediction\n".format(kw['dist_type']))

    def _accum_df(self, ipath: str, opath: str, src_stem: str) -> pd.DataFrame:
        if core.utils.path_exists(opath):
            cum_df = core.utils.pd_csv_read(opath)
        else:
            cum_df = None

        if core.utils.path_exists(ipath):
            t = core.utils.pd_csv_read(ipath)
            if cum_df is None:
                cum_df = pd.DataFrame(columns=t.columns)

            if len(t.index) != 1:
                self.logger.warning("'%s.csv' is a collated inter-experiment csv, not a summary inter-experiment csv:  # rows %s != 1",
                                    src_stem,
                                    len(t.index))
                self.logger.warning("Truncating '%s.csv' to last row", src_stem)

            cum_df = cum_df.append(t.loc[t.index[-1], t.columns.to_list()])
            return cum_df

        return None


__api__ = ['UnivarInterScenarioComparator']
