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
Classes for handling univariate and bivariate controller comparisons within a set of scenarios for
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
from core.graphs.summary_line_graph import SummaryLinegraph
from core.graphs.stacked_surface_graph import StackedSurfaceGraph
from core.graphs.heatmap import Heatmap, DualHeatmap
from core.variables import batch_criteria as bc
import core.root_dirpath_generator as rdg
import core.utils
import core.config


class UnivarIntraScenarioComparator:
    """
    Compares a set of controllers on different performance measures in all scenarios using
    univariate batch criteria, one at a time. Graph generation is controlled via a config file
    parsed in :class:`~core.pipeline.stage5.pipeline_stage5.PipelineStage5`. Univariate batch
    criteria only.

    Attributes:
        controllers: List of controller names to compare.
        cc_csv_root: Absolute directory path to the location controller ``.csv`` files should be
                     output to.
        cc_graph_root: Absolute directory path to the location the generated graphs should be output
                       to.
        cmdopts: Dictionary of parsed cmdline parameters.
        cli_args: :class:`argparse` object containing the cmdline parameters. Needed for
                  :class:`~core.variables.batch_criteria.BatchCriteria` generation for each scenario
                  controllers are compared within, as batch criteria is dependent on
                  controller+scenario definition, and needs to be re-generated for each scenario in
                  order to get graph labels/axis ticks to come out right in all cases.

    """

    def __init__(self,
                 controllers: tp.List[str],
                 cc_csv_root: str,
                 cc_graph_root: str,
                 cmdopts: dict,
                 cli_args,
                 main_config: dict) -> None:
        self.controllers = controllers
        self.cc_graph_root = cc_graph_root
        self.cc_csv_root = cc_csv_root

        self.cmdopts = cmdopts
        self.cli_args = cli_args
        self.main_config = main_config
        self.logger = logging.getLogger(__name__)

    def __call__(self,
                 graphs: dict,
                 legend: tp.List[str],
                 comp_type: str) -> None:
        # Obtain the list of scenarios to use. We can just take the scenario list of the first
        # controllers, because we have already checked that all controllers executed the same set
        # scenarios
        batch_leaves = os.listdir(os.path.join(self.cmdopts['sierra_root'],
                                               self.cmdopts['project'],
                                               self.controllers[0]))

        # The FS gives us batch leaves which might not be in the same order as the list of specified
        # scenarios, so we:
        #
        # 1. Remove all batch leaves which do not have a counterpart in the controller list we are
        #    comparing across.
        # 2. Do matching to get the indices of the batch leaves relative to the list, and then sort
        #    it.
        batch_leaves = [leaf for leaf in batch_leaves for s in self.controllers if s in leaf]
        indices = [self.controllers.index(s)
                   for leaf in batch_leaves for s in self.controllers if s in leaf]
        batch_leaves = [leaf for s, leaf in sorted(zip(indices, batch_leaves),
                                                   key=lambda pair: pair[0])]

        # For each controller comparison graph we are interested in, generate it using data from all
        # scenarios
        cmdopts = copy.deepcopy(self.cmdopts)
        for graph in graphs:
            found = False
            for leaf in batch_leaves:
                if self._leaf_select(leaf):
                    self._compare_in_scenario(cmdopts=cmdopts,
                                              graph=graph,
                                              batch_leaf=leaf,
                                              legend=legend)
                    found = True
                    break
            if not found:
                self.logger.warning("Did not find scenario to compare in for criteria %s",
                                    self.cli_args.batch_criteria)

    def _leaf_select(self, candidate: str) -> bool:
        """
        Select which scenario to compare controllers within. You can only compare controllers within
        the scenario directly generated from the value of ``--batch-criteria``; other scenarios will
        (probably) cause file not found errors.

        """
        template_stem, scenario, _ = rdg.parse_batch_leaf(candidate)
        leaf = rdg.gen_batch_leaf(criteria=self.cli_args.batch_criteria,
                                  scenario=scenario,
                                  template_stem=template_stem)
        return leaf in candidate

    def _compare_in_scenario(self,
                             cmdopts: dict,
                             graph: dict,
                             batch_leaf: str,
                             legend: tp.List[str]) -> None:

        for controller in self.controllers:
            dirs = [d for d in os.listdir(os.path.join(self.cmdopts['sierra_root'],
                                                       self.cmdopts['project'],
                                                       controller)) if batch_leaf in d]
            if len(dirs) == 0:
                self.logger.warning("Controller %s was not run on experiment %s",
                                    controller,
                                    batch_leaf)
                continue

            batch_leaf = dirs[0]
            _, scenario, _ = rdg.parse_batch_leaf(batch_leaf)

            # We need to generate the root directory paths for each batched experiment
            # (which # lives inside of the scenario dir), because they are all
            # different. We need generate these paths for EACH controller, because the
            # controller is part of the batch root path.
            paths = rdg.regen_from_exp(sierra_rpath=self.cli_args.sierra_root,
                                       project=self.cli_args.project,
                                       batch_leaf=batch_leaf,
                                       controller=controller)
            cmdopts.update(paths)

            # For each scenario, we have to create the batch criteria for it, because they
            # are all different.

            criteria = bc.factory(self.main_config, cmdopts, self.cli_args, scenario)

            self._gen_csv(cmdopts=cmdopts,
                          batch_leaf=batch_leaf,
                          controller=controller,
                          src_stem=graph['src_stem'],
                          dest_stem=graph['dest_stem'])

        self._gen_graph(batch_leaf=batch_leaf,
                        criteria=criteria,
                        cmdopts=cmdopts,
                        dest_stem=graph['dest_stem'],
                        title=graph['title'],
                        label=graph['label'],
                        legend=legend)

    def _gen_csv(self,
                 cmdopts: dict,
                 batch_leaf: str,
                 controller: str,
                 src_stem: str,
                 dest_stem: str) -> None:
        """
        Helper function for generating a set of .csv files for use in intra-scenario graph generation
        (1 per controller).
        """

        ipath = os.path.join(cmdopts['batch_stat_collate_root'], src_stem)

        # Some experiments might not generate the necessary performance measure .csvs for graph
        # generation, which is OK.
        if not core.utils.path_exists(ipath):
            self.logger.warning("%s missing for controller %s", ipath, controller)
            return

        _stats_prepare(ipath_stem=cmdopts['batch_stat_collate_root'],
                       ipath_leaf=src_stem,
                       opath_stem=self.cc_csv_root,
                       opath_leaf=LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, None),
                       index=0)

    def _gen_graph(self,
                   batch_leaf: str,
                   criteria: bc.IConcreteBatchCriteria,
                   cmdopts: dict,
                   dest_stem: str,
                   title: str,
                   label: str,
                   legend: tp.List[str]) -> None:
        """
        Generates a :class:`~core.graphs.summary_line_graph.SummaryLinegraph` comparing the
        specified controllers within the specified scenario after input files have been gathered
        from each controller into :attr:`cc_csv_root`.
        """
        opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, None)

        xticks = criteria.graph_xticks(cmdopts)
        xtick_labels = criteria.graph_xticklabels(cmdopts)
        opath = os.path.join(self.cc_graph_root,
                             opath_leaf + core.config.kImageExt)

        SummaryLinegraph(stats_root=self.cc_csv_root,
                         input_stem=opath_leaf,
                         output_fpath=opath,
                         stats=cmdopts['dist_stats'],
                         title=title,
                         xlabel=criteria.graph_xlabel(cmdopts),
                         ylabel=label,
                         xtick_labels=xtick_labels[criteria.inter_exp_graphs_exclude_exp0():],
                         xticks=xticks[criteria.inter_exp_graphs_exclude_exp0():],
                         logyscale=cmdopts['plot_log_yscale'],
                         large_text=self.cmdopts['plot_large_text'],
                         legend=legend).generate()


class BivarIntraScenarioComparator:
    """
    Compares a set of controllers on different performance measures in all scenarios, one at a
    time. Graph generation is controlled via a config file parsed in
    :class:`~core.pipeline.stage5.pipeline_stage5.PipelineStage5`. Bivariate batch criteria only.

    Attributes:
        controllers: List of controller names to compare.
        cc_csv_root: Absolute directory path to the location controller ``.csv`` files should be
                     output to.
        cc_graph_root: Absolute directory path to the location the generated graphs should be output
                       to.
        cmdopts: Dictionary of parsed cmdline parameters.
        cli_args: :class:`argparse` object containing the cmdline parameters. Needed for
                  :class:`~core.variables.batch_criteria.BatchCriteria` generation for each scenario
                  controllers are compared within, as batch criteria is dependent on
                  controller+scenario definition, and needs to be re-generated for each scenario in
                  order to get graph labels/axis ticks to come out right in all cases.
    """

    def __init__(self,
                 controllers: tp.List[str],
                 cc_csv_root: str,
                 cc_graph_root: str,
                 cmdopts: dict,
                 cli_args: argparse.Namespace,
                 main_config: dict) -> None:
        self.controllers = controllers
        self.cc_csv_root = cc_csv_root
        self.cc_graph_root = cc_graph_root
        self.cmdopts = cmdopts
        self.cli_args = cli_args
        self.main_config = main_config
        self.logger = logging.getLogger(__name__)

    def __call__(self,
                 graphs: dict,
                 legend: tp.List[str],
                 comp_type: str) -> None:

        # Obtain the list of scenarios to use. We can just take the scenario list of the first
        # controllers, because we have already checked that all controllers executed the same set
        # scenarios
        batch_leaves = os.listdir(os.path.join(self.cmdopts['sierra_root'],
                                               self.cmdopts['project'],
                                               self.controllers[0]))

        cmdopts = copy.deepcopy(self.cmdopts)
        for graph in graphs:
            found = False
            for leaf in batch_leaves:
                if self._leaf_select(leaf):
                    self._compare_in_scenario(cmdopts=cmdopts,
                                              graph=graph,
                                              batch_leaf=leaf,
                                              legend=legend,
                                              comp_type=comp_type)
                    found = True
                    break
            if not found:
                self.logger.warning("Did not find scenario to compare in for criteria '%s'",
                                    self.cli_args.batch_criteria)

    def _leaf_select(self, candidate: str) -> bool:
        """
        Select which scenario to compare controllers within. You can only compare controllers within
        the scenario directly generated from the value of ``--batch-criteria``; other scenarios will
        (probably) cause file not found errors.

        """
        template_stem, scenario, _ = rdg.parse_batch_leaf(candidate)
        leaf = rdg.gen_batch_leaf(criteria=self.cli_args.batch_criteria,
                                  scenario=scenario,
                                  template_stem=template_stem)
        return leaf in candidate

    def _compare_in_scenario(self,
                             cmdopts: dict,
                             graph: dict,
                             batch_leaf: str,
                             legend: tp.List[str],
                             comp_type: str) -> None:
        """
        Compares all controllers within the specified scenario, generating ``.csv`` files and graphs
        according to configuration.
        """
        for controller in self.controllers:
            dirs = [d for d in os.listdir(os.path.join(self.cmdopts['sierra_root'],
                                                       self.cmdopts['project'],
                                                       controller)) if batch_leaf in d]
            if len(dirs) == 0:
                self.logger.warning("Controller '%s' was not run on scenario '%s'",
                                    controller,
                                    batch_leaf)
                continue

            batch_leaf = dirs[0]
            _, scenario, _ = rdg.parse_batch_leaf(batch_leaf)

            # We need to generate the root directory paths for each batched experiment
            # (which # lives inside of the scenario dir), because they are all
            # different. We need generate these paths for EACH controller, because the
            # controller is part of the batch root path.
            paths = rdg.regen_from_exp(sierra_rpath=self.cli_args.sierra_root,
                                       project=self.cli_args.project,
                                       batch_leaf=batch_leaf,
                                       controller=controller)

            cmdopts.update(paths)

            # For each scenario, we have to create the batch criteria for it, because they
            # are all different.
            criteria = bc.factory(self.main_config, cmdopts, self.cli_args, scenario)

            if comp_type == 'LNraw':
                self._gen_csvs_for_1D(cmdopts=cmdopts,
                                      controller=controller,
                                      batch_leaf=batch_leaf,
                                      src_stem=graph['src_stem'],
                                      dest_stem=graph['dest_stem'])

            elif 'HM' in comp_type or 'SU' in comp_type:
                self._gen_csvs_for_2D_or_3D(cmdopts=cmdopts,
                                            controller=controller,
                                            batch_leaf=batch_leaf,
                                            src_stem=graph['src_stem'],
                                            dest_stem=graph['dest_stem'])

        if comp_type == 'LNraw':
            self._gen_graphs1D(batch_leaf=batch_leaf,
                               criteria=criteria,
                               cmdopts=cmdopts,
                               dest_stem=graph['dest_stem'],
                               title=graph['title'],
                               label=graph['label'],
                               legend=legend)
        elif 'HM' in comp_type:
            self._gen_graphs2D(batch_leaf=batch_leaf,
                               criteria=criteria,
                               cmdopts=cmdopts,
                               dest_stem=graph['dest_stem'],
                               title=graph['title'],
                               label=graph['label'],
                               legend=legend,
                               comp_type=comp_type)

        elif 'SU' in comp_type:
            self._gen_graph3D(batch_leaf=batch_leaf,
                              criteria=criteria,
                              cmdopts=cmdopts,
                              dest_stem=graph['dest_stem'],
                              title=graph['title'],
                              zlabel=graph['label'],
                              legend=legend,
                              comp_type=comp_type)

    def _gen_csvs_for_2D_or_3D(self,
                               cmdopts: dict,
                               batch_leaf: str,
                               controller: str,
                               src_stem: str,
                               dest_stem: str) -> None:
        """
        Helper function for generating a set of .csv files for use in intra-scenario graph
        generation (1 per controller) for 2D/3D comparison types. Because each ``.csv`` file
        corresponding to performance measures are 2D arrays, we actually just copy and rename the
        performance measure ``.csv`` files for each controllers into :attr:`cc_csv_root`.

        :class:`~core.graphs.stacked_surface_graph.StackedSurfaceGraph` expects an ``_[0-9]+.csv``
        pattern for each 2D surfaces to graph in order to disambiguate which files belong to which
        controller without having the controller name in the filepath (contains dots), so we do that
        here. :class:`~core.graphs.heatmap.Heatmap` does not require that, but for the heatmap set
        we generate it IS helpful to have an easy way to differentiate primary vs. other
        controllers, so we do it unconditionally here to handle both cases.

        """
        csv_ipath = os.path.join(cmdopts['batch_stat_collate_root'], src_stem + ".csv")

        # Some experiments might not generate the necessary performance measure .csvs for
        # graph generation, which is OK.
        if not core.utils.path_exists(csv_ipath):
            self.logger.warning("%s missing for controller '%s'", csv_ipath, controller)
            return

        df = core.utils.pd_csv_read(csv_ipath)

        opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf,
                                                   dest_stem,
                                                   [self.controllers.index(controller)])

        csv_opath_stem = os.path.join(self.cc_csv_root, opath_leaf)
        core.utils.pd_csv_write(df, csv_opath_stem + '.csv', index=False)

    def _gen_csvs_for_1D(self,
                         cmdopts: dict,
                         batch_leaf: str,
                         controller: str,
                         src_stem: str,
                         dest_stem: str) -> None:
        """
        Helper function for generating a set of .csv files for use in intra-scenario graph
        generation. Because we are targeting linegraphs, we draw the the i-th row/col (as
        configured) from the performance results of each controller .csv, and concatenate them into
        a new .csv file which can be given to
        :class:`~core.graphs.summary_line_graph.SummaryLinegraph`.
        """
        csv_ipath = os.path.join(cmdopts['batch_stat_collate_root'], src_stem + ".csv")

        # Some experiments might not generate the necessary performance measure .csvs for
        # graph generation, which is OK.
        if not core.utils.path_exists(csv_ipath):
            self.logger.warning("%s missing for controller '%s'", csv_ipath, controller)
            return

        n_rows = len(core.utils.pd_csv_read(os.path.join(cmdopts['batch_stat_collate_root'],
                                                         src_stem + ".csv")).index)

        for i in range(0, n_rows):
            opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, [i])
            _stats_prepare(ipath_stem=cmdopts['batch_stat_collate_root'],
                           ipath_leaf=src_stem,
                           opath_stem=self.cc_csv_root,
                           opath_leaf=opath_leaf,
                           index=i)

    def _gen_graphs1D(self,
                      batch_leaf: str,
                      criteria: bc.BivarBatchCriteria,
                      cmdopts: dict,
                      dest_stem: str,
                      title: str,
                      label: str,
                      legend: tp.List[str]) -> None:
        oleaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, None)
        csv_stem_root = os.path.join(self.cc_csv_root, oleaf)
        paths = [f for f in glob.glob(csv_stem_root + '*.csv') if re.search('_[0-9]+', f)]

        for i in range(0, len(paths)):
            opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, [i])
            img_opath = os.path.join(self.cc_graph_root, opath_leaf + core.config.kImageExt)

            SummaryLinegraph(stats_root=self.cc_csv_root,
                             input_stem=opath_leaf,
                             stats=cmdopts['dist_stats'],
                             output_fpath=img_opath,
                             model_root=cmdopts['batch_model_root'],
                             title=title,
                             xlabel=criteria.graph_xlabel(cmdopts),
                             ylabel=label,
                             xticks=criteria.graph_xticks(cmdopts),
                             legend=legend,
                             logyscale=cmdopts['plot_log_yscale'],
                             large_text=cmdopts['plot_large_text']).generate()

    def _gen_graphs2D(self,
                      batch_leaf: str,
                      criteria: bc.BivarBatchCriteria,
                      cmdopts: dict,
                      dest_stem: str,
                      title: str,
                      label: str,
                      legend: tp.List[str],
                      comp_type: str) -> None:
        if comp_type in ['HMscale', 'HMdiff']:
            self._gen_paired_heatmaps(batch_leaf,
                                      criteria,
                                      cmdopts,
                                      dest_stem,
                                      title,
                                      label,
                                      comp_type)
        elif comp_type == 'HMraw':
            self._gen_dual_heatmaps(batch_leaf,
                                    criteria,
                                    cmdopts,
                                    dest_stem,
                                    title,
                                    label,
                                    legend,
                                    comp_type)

    def _gen_paired_heatmaps(self,
                             batch_leaf: str,
                             criteria: bc.BivarBatchCriteria,
                             cmdopts: dict,
                             dest_stem: str,
                             title: str,
                             label: str,
                             comp_type: str) -> None:
        """
        Generates a set of :class:`~core.graphs.heatmap.Heatmap` graphs a controller of primary
        interest against all other controllers (one graph per pairing), after input files have been
        gathered from each controller into :attr:`cc_csv_root`. Only valid if the
        comparison type is ``scale2D`` or ``diff2D``.
        """
        opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, None)
        csv_pattern_root = os.path.join(self.cc_csv_root, opath_leaf)
        paths = [f for f in glob.glob(csv_pattern_root + '*.csv') if re.search('_[0-9]+', f)]

        ref_df = core.utils.pd_csv_read(paths[0])

        for i in range(1, len(paths)):
            df = core.utils.pd_csv_read(paths[i])

            if comp_type == 'HMscale':
                plot_df = df / ref_df
            elif comp_type == 'HMdiff':
                plot_df = df - ref_df

            opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, [0, i])
            opath_stem = os.path.join(self.cc_csv_root, opath_leaf)
            opath = opath_stem + core.config.kImageExt

            core.utils.pd_csv_write(plot_df, opath_stem + ".csv", index=False)

            Heatmap(input_fpath=opath_stem + ".csv",
                    output_fpath=opath,
                    title=title,
                    transpose=self.cmdopts['transpose_graphs'],
                    zlabel=self._gen_zaxis_label(label, comp_type),
                    xlabel=criteria.graph_xlabel(cmdopts),
                    ylabel=criteria.graph_ylabel(cmdopts),
                    xtick_labels=criteria.graph_xticklabels(cmdopts),
                    ytick_labels=criteria.graph_yticklabels(cmdopts)).generate()

    def _gen_dual_heatmaps(self,
                           batch_leaf: str,
                           criteria: bc.BivarBatchCriteria,
                           cmdopts: dict,
                           dest_stem: str,
                           title: str,
                           label: str,
                           legend: tp.List[str],
                           comp_type: str) -> None:
        """
        Generates a set of :class:`~core.graphs.heatmap.DualHeatmap` graphs containing all pairs of
        (primary controller, other), one per graph, within the specified scenario after input files
        have been gathered from each controller into :attr:`cpc_csv_root`. Only valid if
        the comparison type is ``raw``.
        """

        opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, None)
        csv_pattern_root = os.path.join(self.cc_csv_root, opath_leaf)
        print(csv_pattern_root)
        paths = [f for f in glob.glob(csv_pattern_root + '*.csv') if re.search('_[0-9]+', f)]

        for i in range(0, len(paths)):
            opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, None)
            opath = os.path.join(self.cc_graph_root, opath_leaf + core.config.kImageExt)

            DualHeatmap(input_stem_pattern=csv_pattern_root,
                        output_fpath=opath,
                        title=title,
                        zlabel=self._gen_zaxis_label(label, comp_type),
                        xlabel=criteria.graph_xlabel(cmdopts),
                        ylabel=criteria.graph_ylabel(cmdopts),
                        legend=legend,
                        xtick_labels=criteria.graph_xticklabels(cmdopts),
                        ytick_labels=criteria.graph_yticklabels(cmdopts)).generate()

    def _gen_graph3D(self,
                     batch_leaf: str,
                     criteria: bc.BivarBatchCriteria,
                     cmdopts: dict,
                     dest_stem: str,
                     title: str,
                     zlabel: str,
                     legend: tp.List[str],
                     comp_type: str) -> None:
        """
        Generates a :class:`~core.graphs.stacked_surface_graph.StackedSurfaceGraph` comparing the
        specified controllers within thespecified scenario after input files have been gathered from
        each controllers into :attr:`cc_csv_root`.
        """

        opath_leaf = LeafGenerator.from_batch_leaf(batch_leaf, dest_stem, None)
        csv_stem_root = os.path.join(self.cc_csv_root, opath_leaf)
        opath = os.path.join(self.cc_graph_root, opath_leaf + core.config.kImageExt)

        StackedSurfaceGraph(input_stem_pattern=csv_stem_root,
                            output_fpath=opath,
                            title=title,
                            ylabel=criteria.graph_xlabel(cmdopts),
                            xlabel=criteria.graph_ylabel(cmdopts),
                            zlabel=self._gen_zaxis_label(zlabel, comp_type),
                            xtick_labels=criteria.graph_yticklabels(cmdopts),
                            ytick_labels=criteria.graph_xticklabels(cmdopts),
                            legend=legend,
                            comp_type=comp_type).generate()

    def _gen_zaxis_label(self, label: str, comp_type: str) -> str:
        """
        If we are doing something other than raw controller comparisons, put that on the graph
        Z axis title.
        """
        if 'scale' in comp_type:
            return label + ' (Scaled)'
        elif 'diff' in comp_type == comp_type:
            return label + ' (Difference Comparison)'
        return label


def _stats_prepare(ipath_stem: str,
                   ipath_leaf: str,
                   opath_stem: str,
                   opath_leaf: str,
                   index: int) -> None:

    for k in core.config.kStatsExtensions.keys():
        stat_ipath = os.path.join(ipath_stem,
                                  ipath_leaf + core.config.kStatsExtensions[k])
        stat_opath = os.path.join(opath_stem,
                                  opath_leaf + core.config.kStatsExtensions[k])
        df = _accum_df_by_row(stat_ipath, stat_opath, index)

        if df is not None:
            core.utils.pd_csv_write(df,
                                    os.path.join(opath_stem,
                                                 opath_leaf + core.config.kStatsExtensions[k]),
                                    index=False)


def _accum_df_by_row(ipath: str, opath: str, index: int) -> pd.DataFrame:
    if core.utils.path_exists(opath):
        cum_df = core.utils.pd_csv_read(opath)
    else:
        cum_df = None

    if core.utils.path_exists(ipath):
        t = core.utils.pd_csv_read(ipath)
        if cum_df is None:
            cum_df = pd.DataFrame(columns=t.columns)

        cum_df = cum_df.append(t.loc[index, :])
        return cum_df

    return None


class LeafGenerator():
    @staticmethod
    def from_controller(batch_root: str,
                        graph_stem: str,
                        controllers: tp.List[str],
                        controller) -> str:
        _, batch_leaf, _ = rdg.parse_batch_leaf(batch_root)
        leaf = graph_stem + "-" + batch_leaf + '_' + str(controllers.index(controller))
        return leaf

    @staticmethod
    def from_batch_root(batch_root: str,
                        graph_stem: str,
                        index: tp.Union[int, None]):
        _, scenario, _ = rdg.parse_batch_leaf(batch_root)
        leaf = graph_stem + "-" + scenario

        if index is not None:
            leaf += '_' + str(index)

        return leaf

    @staticmethod
    def from_batch_leaf(batch_leaf: str,
                        graph_stem: str,
                        indices: tp.Union[tp.List[int], None]):
        leaf = graph_stem + "-" + batch_leaf

        if indices is not None:
            leaf += '_' + ''.join([str(i) for i in indices])

        return leaf


__api__ = ['UnivarIntraScenarioComparator', 'BivarIntraScenarioComparator']
