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

"""
Classes for generating graphs across experiments in a batch.
"""

import os
import copy
import logging
import typing as tp

import core.perf_measures.scalability as pms
import core.perf_measures.self_organization as pmso
import core.perf_measures.block_collection as pmbc
import core.perf_measures.robustness as pmb
import core.perf_measures.flexibility as pmf
import core.utils
from core.graphs.stacked_line_graph import StackedLineGraph
from core.variables import batch_criteria as bc


class InterExpGraphGenerator:
    """
    Generates graphs from collated ``.csv`` files across experiments in a batch. Which graphs are
    generated is controlled by (1) YAML configuration files parsed in
    :class:`~pipeline.stage4.PipelineStage4` (2) which batch criteria was used (for performance
    measures).

    """

    def __init__(self, main_config: dict, cmdopts: tp.Dict[str, str], targets: dict) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us
        self.cmdopts = copy.deepcopy(cmdopts)
        self.main_config = main_config
        self.targets = targets

        collate_csv_leaf = self.main_config['sierra']['collate_csv_leaf']
        collate_graph_leaf = self.main_config['sierra']['collate_graph_leaf']
        self.cmdopts["collate_root"] = os.path.abspath(os.path.join(self.cmdopts["output_root"],
                                                                    collate_csv_leaf))
        self.cmdopts["graph_root"] = os.path.abspath(os.path.join(self.cmdopts["graph_root"],
                                                                  collate_graph_leaf))
        core.utils.dir_create_checked(self.cmdopts["graph_root"], exist_ok=True)

    def __call__(self, batch_criteria: bc.UnivarBatchCriteria):
        """
        Runs the following to generate graphs across experiments in the batch:

        #. :class:`~pipeline.stage4.inter_exp_graph_generator.LinegraphsGenerator` to generate
           linegraphs (univariate batch criteria only).

        #. :class:`~pipeline.stage4.inter_exp_graph_generator.UnivarPerfMeasuresGenerator` to
           generate performance measures (univariate batch criteria only).

        #. :class:`~pipeline.stage4.inter_exp_graph_generator.BivarPerfMeasuresGenerator` to
           generate performance measures (bivariate batch criteria only).
        """

        if batch_criteria.is_univar():
            # LinegraphsGenerator(self.cmdopts["collate_root"],
            #                     self.cmdopts["graph_root"],
            #                     self.targets).generate()
            UnivarPerfMeasuresGenerator(self.main_config, self.cmdopts)(batch_criteria)
        else:
            BivarPerfMeasuresGenerator(self.main_config, self.cmdopts)(batch_criteria)


class LinegraphsGenerator:
    """
    Generates linegraphs from collated .csv data across a batch of experiments.

    Attributes:
      collate_root: Absolute path to root directory for collated csvs.
      graph_root: Absolute path to root directory where the generated graphs should be saved.
      targets: Dictionary of parsed YAML configuration controlling what graphs should be generated.
    """

    def __init__(self, collate_root: str, graph_root: str, targets: dict) -> None:
        self.collate_root = collate_root
        self.graph_root = graph_root
        self.targets = targets

    def generate(self):
        logging.info("Linegraphs from %s", self.collate_root)
        # For each category of linegraphs we are generating
        for category in self.targets:
            # For each graph in each category
            for graph in category['graphs']:
                StackedLineGraph(input_stem_fpath=os.path.join(self.collate_root,
                                                               graph['dest_stem']),
                                 output_fpath=os.path.join(
                                     self.graph_root,
                                     graph['dest_stem'] + '.png'),
                                 cols=None,
                                 title=graph['title'],
                                 legend=None,
                                 xlabel=graph['xlabel'],
                                 ylabel=graph['ylabel'],
                                 linestyles=None,
                                 dashes=None).generate()


class UnivarPerfMeasuresGenerator:
    """
    Generates performance measures from collated .csv data across a batch of experiments. Which
    measures are generated is controlled by the batch criteria used for the experiment. Univariate
    batch criteria only.

    Attributes:
        cmdopts: Dictionary of parsed cmdline options.
        main_config: Dictionary of parsed main YAML config.
    """

    def __init__(self, main_config, cmdopts) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us
        self.cmdopts = copy.deepcopy(cmdopts)
        self.main_config = main_config

    def __call__(self, batch_criteria: bc.UnivarBatchCriteria):
        inter_perf_csv = self.main_config['perf']['inter_perf_csv']
        interference_count_csv = self.main_config['perf']['interference_count_csv']
        interference_duration_csv = self.main_config['perf']['interference_duration_csv']

        if batch_criteria.pm_query('blocks-transported'):
            pmbc.BlockCollectionUnivar(self.cmdopts,
                                       inter_perf_csv).generate(batch_criteria)
        if batch_criteria.pm_query('scalability'):
            pms.ScalabilityUnivarGenerator()(inter_perf_csv,
                                             interference_count_csv,
                                             interference_duration_csv,
                                             self.cmdopts,
                                             batch_criteria)

        if batch_criteria.pm_query('self-org'):
            alpha_S = self.main_config['perf']['emergence'].get('alpha_S', 0.5)
            alpha_T = self.main_config['perf']['emergence'].get('alpha_T', 0.5)
            pmso.SelfOrgUnivarGenerator()(self.cmdopts,
                                          inter_perf_csv,
                                          interference_count_csv,
                                          alpha_S,
                                          alpha_T,
                                          batch_criteria)

        if batch_criteria.pm_query('flexibility'):
            alpha_R = self.main_config['perf']['flexibility'].get('alpha_R', 0.5)
            alpha_S = self.main_config['perf']['flexibility'].get('alpha_A', 0.5)
            pmf.FlexibilityUnivarGenerator()(self.cmdopts,
                                             self.main_config,
                                             alpha_R,
                                             alpha_S,
                                             batch_criteria)

        if batch_criteria.pm_query('robustness'):
            alpha_SAA = self.main_config['perf']['robustness'].get('alpha_SAA', 0.5)
            alpha_PD = self.main_config['perf']['robustness'].get('alpha_PD', 0.5)
            pmb.RobustnessUnivarGenerator()(self.cmdopts,
                                            self.main_config,
                                            alpha_SAA,
                                            alpha_PD,
                                            batch_criteria)


class BivarPerfMeasuresGenerator:
    """
    Generates performance measures from collated .csv data across a batch of experiments. Which
    measures are generated is controlled by the batch criteria used for the experiment. Bivariate
    batch criteria only.

    Attributes:
        cmdopts: Dictionary of parsed cmdline options.
        main_config: Dictionary of parsed main YAML config.
    """

    def __init__(self, main_config, cmdopts) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us
        self.cmdopts = copy.deepcopy(cmdopts)
        self.main_config = main_config

    def __call__(self, batch_criteria):
        inter_perf_csv = self.main_config['perf']['inter_perf_csv']
        interference_count_csv = self.main_config['perf']['interference_count_csv']
        interference_duration_csv = self.main_config['perf']['interference_duration_csv']

        if batch_criteria.pm_query('blocks-transported'):
            pmbc.BlockCollectionBivar(self.cmdopts,
                                      inter_perf_csv).generate(batch_criteria)

        if batch_criteria.pm_query('scalability'):
            pms.ScalabilityBivarGenerator()(inter_perf_csv,
                                            interference_count_csv,
                                            interference_duration_csv,
                                            self.cmdopts,
                                            batch_criteria)

        if batch_criteria.pm_query('self-org'):
            alpha_S = self.main_config['perf']['emergence'].get('alpha_S', 0.5)
            alpha_T = self.main_config['perf']['emergence'].get('alpha_T', 0.5)

            pmso.SelfOrgBivarGenerator()(self.cmdopts,
                                         inter_perf_csv,
                                         interference_count_csv,
                                         alpha_S,
                                         alpha_T,
                                         batch_criteria)

        if batch_criteria.pm_query('flexibility'):
            alpha_R = self.main_config['perf']['flexibility'].get('alpha_R', 0.5)
            alpha_S = self.main_config['perf']['flexibility'].get('alpha_A', 0.5)
            pmf.FlexibilityBivarGenerator()(self.cmdopts,
                                            self.main_config,
                                            alpha_R,
                                            alpha_S,
                                            batch_criteria)

        if batch_criteria.pm_query('robustness'):
            alpha_SAA = self.main_config['perf']['robustness'].get('alpha_SAA', 0.5)
            alpha_PD = self.main_config['perf']['robustness'].get('alpha_PD', 0.5)
            pmb.RobustnessBivarGenerator()(self.cmdopts,
                                           self.main_config,
                                           alpha_SAA,
                                           alpha_PD,
                                           batch_criteria)
