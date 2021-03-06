# Copyright 2020 John Harwell, All rights reserved.
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
Classes for measuring the robustness of a swarm configuration in various ways.
"""

# Core packages
import os
import copy
import logging

# 3rd party packages
import pandas as pd

# Project packages
from core.graphs.batch_ranged_graph import BatchRangedGraph
from core.perf_measures import vcs
import core.variables.batch_criteria as bc
from core.graphs.heatmap import Heatmap
from core.graphs.scatterplot2D import Scatterplot2D
import core.variables.saa_noise as saan
import core.perf_measures.common as common
import core.utils
from core.variables.population_dynamics import PopulationDynamics
from core.xml_luigi import XMLAttrChangeSet

kIDEAL_SAA_ROBUSTNESS = 0.0

################################################################################
# Univariate Classes
################################################################################


class RobustnessSAAUnivar:
    """
    Calculates the robustness of the swarm configuration to sensor and actuator noise across a
    univariate batched set of experiments within the same scenario from collated .csv data using
    curve similarity measures.
    """
    kLeaf = 'PM-robustness-saa'

    def __init__(self, cmdopts: dict) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us.
        self.cmdopts = copy.deepcopy(cmdopts)

    def generate(self, main_config: dict, criteria: bc.IConcreteBatchCriteria):
        """
        Generate a robustness graph for a given controller in a given scenario by computing the
        value of the robustness metric for each experiment within the batch (Y values), and plotting
        a line graph from it using the X-values from the specified batch criteria.
        """

        batch_exp_dirnames = criteria.gen_exp_dirnames(self.cmdopts)

        # Robustness is only defined for experiments > 0, as exp0 is assumed to be ideal conditions,
        # so we have to slice. We use the reactivity curve similarity measure because we are
        # interested in how closely the swarm's performnce under noise tracks that of ideal
        # conditions. With perfect SAA robustness, they should track exactly.

        df = pd.DataFrame(columns=batch_exp_dirnames, index=[0])
        df[batch_exp_dirnames[0]] = kIDEAL_SAA_ROBUSTNESS

        for i in range(1, criteria.n_exp()):
            df[batch_exp_dirnames[i]] = vcs.RawPerfCS(main_config,
                                                      self.cmdopts,
                                                      0,
                                                      i)(criteria)

        stem_opath = os.path.join(self.cmdopts["batch_collate_root"], self.kLeaf)

        # Write .csv to file
        core.utils.pd_csv_write(df, stem_opath + '.csv', index=False)

        BatchRangedGraph(input_fpath=stem_opath + '.csv',
                         output_fpath=os.path.join(self.cmdopts["batch_collate_graph_root"],
                                                   self.kLeaf + core.config.kImageExt),
                         title="Swarm Robustness (SAA)",
                         xlabel=criteria.graph_xlabel(self.cmdopts),
                         ylabel=vcs.method_ylabel(self.cmdopts["rperf_cs_method"],
                                                  'robustness_saa'),
                         xticks=criteria.graph_xticks(self.cmdopts),
                         xtick_labels=criteria.graph_xticklabels(self.cmdopts),
                         logyscale=self.cmdopts['plot_log_yscale'],
                         large_text=self.cmdopts['plot_large_text']).generate()


class RobustnessPDUnivar:
    """
    Calculates the robustness of the swarm configuration to population size fluctuations across a
    univariate batched set of experiments within the same scenario from collated .csv data.
    """
    kLeaf = 'PM-robustness-pd'

    def __init__(self, cmdopts: dict,
                 inter_perf_csv: str) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us.
        self.cmdopts = copy.deepcopy(cmdopts)
        self.inter_perf_csv = inter_perf_csv

    def generate(self, criteria: bc.IConcreteBatchCriteria):
        """
        Generate a robustness graph for a given controller in a given scenario by computing the
        value of the robustness metric for each experiment within the batch (Y values), and plotting
        a line graph from it using the X-values from the specified batch criteria.
        """

        batch_exp_dirnames = criteria.gen_exp_dirnames(self.cmdopts)

        df = pd.DataFrame(columns=batch_exp_dirnames, index=[0])
        perf_df = core.utils.pd_csv_read(os.path.join(self.cmdopts["batch_collate_root"],
                                                      self.inter_perf_csv))

        idx = perf_df.index[-1]
        for i in range(0, criteria.n_exp()):
            exp_def = XMLAttrChangeSet.unpickle(os.path.join(self.cmdopts['batch_input_root'],
                                                             batch_exp_dirnames[i],
                                                             core.config.kPickleLeaf))
            TS, T = PopulationDynamics.calc_tasked_swarm_time(exp_def)
            perf0 = perf_df.loc[idx, batch_exp_dirnames[0]]
            perfN = perf_df.loc[idx, batch_exp_dirnames[i]]
            df[batch_exp_dirnames[i]] = calculate_fpr(TS=TS,
                                                      T=T,
                                                      perf0=perf0,
                                                      perfN=perfN,
                                                      normalize=self.cmdopts['pm_robustness_normalize'],
                                                      normalize_method=self.cmdopts['pm_normalize_method'])

        stem_opath = os.path.join(self.cmdopts["batch_collate_root"], self.kLeaf)

        # Write .csv to file
        core.utils.pd_csv_write(df, stem_opath + '.csv', index=False)

        BatchRangedGraph(input_fpath=stem_opath + '.csv',
                         output_fpath=os.path.join(
                             self.cmdopts["batch_collate_graph_root"], self.kLeaf + core.config.kImageExt),
                         title="Swarm Robustness (Population Dynamics)",
                         xlabel=criteria.graph_xlabel(self.cmdopts),
                         ylabel="Robustness Value",
                         xticks=criteria.graph_xticks(self.cmdopts),
                         xtick_labels=criteria.graph_xticklabels(self.cmdopts),
                         logyscale=self.cmdopts['plot_log_yscale'],
                         large_text=self.cmdopts['plot_large_text']).generate()


class RobustnessUnivarGenerator:
    """
    Calculates the robustness of the swarm configuration across a univariate batched set of
    experiments within the same scenario from collated .csv data in the following ways:

    - SAA robustness
    - Population dynamics robustness
    - Weighted SAA robustness+population dynamics robustness
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def __call__(self,
                 cmdopts: dict,
                 main_config: dict,
                 alpha_SAA: float,
                 alpha_PD: float,
                 batch_criteria: bc.IConcreteBatchCriteria):
        self.logger.info("From %s", cmdopts["batch_collate_root"])

        inter_perf_csv = main_config['perf']['inter_perf_csv']

        RobustnessSAAUnivar(cmdopts).generate(main_config, batch_criteria)
        RobustnessPDUnivar(cmdopts, inter_perf_csv).generate(batch_criteria)

        title1 = 'Swarm Robustness '
        title2 = r'($\alpha_{{B_{{SAA}}}}={0},\alpha_{{B_{{PD}}}}={1}$)'.format(alpha_SAA,
                                                                                alpha_PD)
        w = common.WeightedPMUnivar(cmdopts=cmdopts,
                                    output_leaf='pm-robustness',
                                    ax1_leaf=RobustnessSAABivar.kLeaf,
                                    ax2_leaf=RobustnessPDBivar.kLeaf,
                                    ax1_alpha=alpha_SAA,
                                    ax2_alpha=alpha_PD,
                                    title=title1 + title2)
        w.generate(batch_criteria)

################################################################################
# Bivariate Classes
################################################################################


class RobustnessSAABivar:
    """
    Calculates the robustness of the swarm configuration to sensor and actuator noise across a
    bivariate batched set of experiments within the same scenario from collated .csv data using
    curve similarity measures.
    """
    kLeaf = "pm-robustness-saa"

    def __init__(self, cmdopts: dict, inter_perf_csv: str) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us
        self.cmdopts = copy.deepcopy(cmdopts)
        self.inter_perf_csv = inter_perf_csv

    def generate(self, main_config: dict, criteria: bc.IConcreteBatchCriteria):
        """
        - :class:`~core.graphs.heatmap.Heatmap` of robustness values for the bivariate batch
          criteria.
        - :class:`~core.graphs.scatterplot2D.Scatterplot2D` of performance vs. robustness for
          regression purposes.
        """
        csv_ipath = self.__gen_heatmap(main_config, criteria)
        self.__gen_scatterplot(csv_ipath, criteria)

    def __gen_scatterplot(self, rob_ipath: str, criteria: bc.BivarBatchCriteria):
        """
        Generate a :class:`~core.graphs.scatterplot2D.Scatterplot2D` graph of robustness
        vs. performance AFTER the main robustness `.csv` has generated in :method:`__gen_heatmap()`
        """
        perf_ipath = os.path.join(self.cmdopts["batch_collate_root"], self.inter_perf_csv)
        opath = os.path.join(self.cmdopts['batch_collate_root'], self.kLeaf + '-vs-perf.csv')
        perf_df = core.utils.pd_csv_read(perf_ipath)
        rob_df = core.utils.pd_csv_read(rob_ipath)
        scatter_df = pd.DataFrame(columns=['perf', 'robustness-saa'])

        # The inter-perf csv has temporal sequences at each (i,j) location, so we need to reduce
        # each of those to a single scalar: the cumulate measure of performance.
        for i in range(0, len(perf_df.index)):
            for j in range(0, len(perf_df.columns)):
                n_blocks = common.csv_3D_value_iloc(perf_df,
                                                    i,
                                                    j,
                                                    slice(-1, None))
                perf_df.iloc[i, j] = n_blocks

        scatter_df['perf'] = perf_df.values.flatten()
        scatter_df['robustness-saa'] = rob_df.values.flatten()
        core.utils.pd_csv_write(scatter_df, opath, index=False)

        Scatterplot2D(input_fpath=opath,
                      output_fpath=os.path.join(self.cmdopts["batch_collate_graph_root"],
                                                self.kLeaf + "-vs-perf" + core.config.kImageExt),
                      title='Swarm Robustness (SAA) vs. Performance',
                      xcol='robustness-saa',
                      ycol='perf',
                      regression=self.cmdopts['plot_regression_lines'],
                      xlabel='Robustness (SAA)',
                      ylabel=criteria.graph_ylabel(self.cmdopts)).generate()

    def __gen_heatmap(self, main_config: dict, criteria: bc.IConcreteBatchCriteria):
        """
        Generate a robustness graph for a given controller in a given scenario by computing the
        value of the robustness metric for each experiment within the batch, and plot
        a :class:`~core.graphs.heatmap.Heatmap` of the robustness variable vs. the other one.

        Returns:
           The path to the `.csv` file used to generate the heatmap.
        """
        ipath = os.path.join(self.cmdopts["batch_collate_root"], self.inter_perf_csv)
        raw_df = core.utils.pd_csv_read(ipath)
        opath_stem = os.path.join(self.cmdopts["batch_collate_root"], self.kLeaf)

        # Generate heatmap dataframe and write to file
        df = self.__gen_heatmap_df(main_config, raw_df, criteria)
        core.utils.pd_csv_write(df, opath_stem + ".csv", index=False)

        Heatmap(input_fpath=opath_stem + '.csv',
                output_fpath=os.path.join(
                    self.cmdopts["batch_collate_graph_root"], self.kLeaf + core.config.kImageExt),
                title='Swarm Robustness (SAA)',
                xlabel=criteria.graph_xlabel(self.cmdopts),
                ylabel=criteria.graph_ylabel(self.cmdopts),
                xtick_labels=criteria.graph_xticklabels(self.cmdopts),
                ytick_labels=criteria.graph_yticklabels(self.cmdopts)).generate()
        return opath_stem + '.csv'

    def __gen_heatmap_df(self,
                         main_config: dict,
                         raw_df: pd.DataFrame,
                         criteria: bc.BivarBatchCriteria):
        df = pd.DataFrame(columns=raw_df.columns, index=raw_df.index)

        for i in range(0, len(df.index)):
            for j in range(0, len(df.columns)):
                # We need to know which of the 2 variables was SAA noise, in order to determine the
                # correct dimension along which to compute the metric.
                axis = core.utils.get_primary_axis(criteria, [saan.SAANoise], self.cmdopts)
                if axis == 0:
                    val = vcs.RawPerfCS(main_config,
                                        self.cmdopts,
                                        j,  # exp0 in first row with i=0
                                        i * len(df.columns) + j)(criteria)
                else:
                    val = vcs.RawPerfCS(main_config,
                                        self.cmdopts,
                                        i * len(df.columns),  # exp0 in first col with j=0
                                        i * len(df.columns) + j)(criteria)

                df.iloc[i, j] = val
        return df


class RobustnessPDBivar:
    """
    Calculates the robustness of the swarm configuration to fluctuating population sies across a
    bivariate batched set of experiments within the same scenario from collated .csv data.
    """
    kLeaf = "pm-robustness-pd"

    def __init__(self, cmdopts: dict, inter_perf_csv: str) -> None:
        # Copy because we are modifying it and don't want to mess up the arguments for graphs that
        # are generated after us
        self.cmdopts = copy.deepcopy(cmdopts)
        self.inter_perf_csv = inter_perf_csv

    def generate(self, criteria: bc.BivarBatchCriteria):
        """
        - :class:`~core.graphs.heatmap.Heatmap` of robustness values for the bivariate batch
          criteria
        - :class:`~core.graphs.scatterplot2D.Scatterplot2D` of performance vs. robustness for
          regression purposes.
        """
        csv_ipath = self.__gen_heatmap(criteria)
        self.__gen_scatterplot(csv_ipath, criteria)

    def __gen_scatterplot(self, rob_ipath: str, criteria: bc.BivarBatchCriteria):
        """
        Generate a :class:`~core.graphs.scatterplot2D.Scatterplot2D` graph of robustness
        vs. performance AFTER the main robustness `.csv` has generated in :method:`__gen_heatmap()`
        """
        perf_ipath = os.path.join(self.cmdopts["batch_collate_root"], self.inter_perf_csv)
        opath = os.path.join(self.cmdopts['batch_collate_root'],
                             self.kLeaf + '-vs-perf.csv')
        perf_df = core.utils.pd_csv_read(perf_ipath)
        rob_df = core.utils.pd_csv_read(rob_ipath)
        scatter_df = pd.DataFrame(columns=['perf', 'robustness-size'])

        # The inter-perf csv has temporal sequences at each (i,j) location, so we need to reduce
        # each of those to a single scalar: the cumulate measure of performance.
        for i in range(0, len(perf_df.index)):
            for j in range(0, len(perf_df.columns)):
                n_blocks = common.csv_3D_value_iloc(perf_df,
                                                    i,
                                                    j,
                                                    slice(-1, None))
                perf_df.iloc[i, j] = n_blocks

        scatter_df['perf'] = perf_df.values.flatten()
        scatter_df['robustness-size'] = rob_df.values.flatten()
        core.utils.pd_csv_write(scatter_df, opath, index=False)

        Scatterplot2D(input_fpath=opath,
                      output_fpath=os.path.join(self.cmdopts["batch_collate_graph_root"],
                                                self.kLeaf + "-vs-perf" + core.config.kImageExt),
                      title='Swarm Robustness (Fluctuating Population) vs. Performance',
                      xcol='robustness-size',
                      ycol='perf',
                      regression=self.cmdopts['plot_regression_lines'],
                      xlabel='Robustness Value',
                      ylabel=criteria.graph_ylabel(self.cmdopts)).generate()

    def __gen_heatmap(self, criteria: bc.BivarBatchCriteria):
        """
        Generate a robustness graph for a given controller in a given scenario by computing the
        value of the robustness metric for each experiment within the batch, and plot
        a :class:`~core.graphs.heatmap.Heatmap` of the robustness variable vs. the other one.

        Returns:
           The path to the `.csv` file used to generate the heatmap.
        """
        ipath = os.path.join(self.cmdopts["batch_collate_root"], self.inter_perf_csv)
        raw_df = core.utils.pd_csv_read(ipath, )
        opath_stem = os.path.join(self.cmdopts["batch_collate_root"], self.kLeaf)

        # Generate heatmap dataframe and write to file
        df = self.__gen_heatmap_df(raw_df, criteria)
        core.utils.pd_csv_write(df, opath_stem + ".csv", index=False)

        Heatmap(input_fpath=opath_stem + '.csv',
                output_fpath=os.path.join(
                    self.cmdopts["batch_collate_graph_root"], self.kLeaf + core.config.kImageExt),
                title='Swarm Robustness (Fluctuating Populations)',
                xlabel=criteria.graph_xlabel(self.cmdopts),
                ylabel=criteria.graph_ylabel(self.cmdopts),
                xtick_labels=criteria.graph_xticklabels(self.cmdopts),
                ytick_labels=criteria.graph_yticklabels(self.cmdopts)).generate()
        return opath_stem + '.csv'

    def __gen_heatmap_df(self, raw_df: pd.DataFrame, criteria: bc.BivarBatchCriteria):
        df = pd.DataFrame(columns=raw_df.columns, index=raw_df.index)

        exp_dirnames = criteria.gen_exp_dirnames(self.cmdopts)
        for i in range(0, len(df.index)):
            for j in range(0, len(df.columns)):
                pkl_path = os.path.join(self.cmdopts['batch_input_root'],
                                        exp_dirnames[i * len(df.columns) + j],
                                        core.config.kPickleLeaf)
                exp_def = XMLAttrChangeSet.unpickle(pkl_path)

                TS, T = PopulationDynamics.calc_tasked_swarm_time(exp_def)

                # We need to know which of the 2 variables was SAA noise, in order to determine the
                # correct dimension along which to compute the metric.
                axis = core.utils.get_primary_axis(criteria, [PopulationDynamics], self.cmdopts)
                if axis == 0:
                    perf0 = common.csv_3D_value_iloc(raw_df,
                                                     0,  # exp0 in first row with i=0
                                                     j,
                                                     slice(-1, None))
                else:
                    perf0 = common.csv_3D_value_iloc(raw_df,
                                                     i,
                                                     0,  # exp0 in first col with j=0
                                                     slice(-1, None))

                perfN = common.csv_3D_value_iloc(raw_df,
                                                 i,
                                                 j,
                                                 slice(-1, None))
                df.iloc[i, j] = calculate_fpr(TS=TS,
                                              T=T,
                                              perfN=perfN,
                                              perf0=perf0,
                                              normalize=self.cmdopts['pm_robustness_normalize'],
                                              normalize_method=self.cmdopts['pm_normalize_method'])
        return df


class RobustnessBivarGenerator:
    """
    Calculates the robustness of the swarm configuration across a bivariate batched set of
    experiments within the same scenario from collated .csv data in the following ways:

    - SAA robustness
    - Population dynamics robustness
    - Weighted SAA robustness+population dynamics robustness
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def __call__(self,
                 cmdopts: dict,
                 main_config: dict,
                 alpha_SAA: float,
                 alpha_PD: float,
                 batch_criteria: bc.IConcreteBatchCriteria):
        self.logger.info("From %s", cmdopts["batch_collate_root"])

        inter_perf_csv = main_config['perf']['inter_perf_csv']

        RobustnessSAABivar(cmdopts, inter_perf_csv).generate(main_config, batch_criteria)
        RobustnessPDBivar(cmdopts, inter_perf_csv).generate(batch_criteria)

        title1 = r'Swarm Robustness '
        title2 = r'($\alpha_{{B_{{SAA}}}}={0},\alpha_{{B_{{PD}}}}={1}$)'.format(alpha_SAA,
                                                                                alpha_PD)
        w = common.WeightedPMBivar(cmdopts=cmdopts,
                                   output_leaf='pm-robustness',
                                   ax1_leaf=RobustnessSAAUnivar.kLeaf,
                                   ax2_leaf=RobustnessPDUnivar.kLeaf,
                                   ax1_alpha=alpha_SAA,
                                   ax2_alpha=alpha_PD,
                                   title=title1 + title2)
        w.generate(batch_criteria)

################################################################################
# Calculation Functions
################################################################################


def calculate_fpr(TS: float,
                  T: int,
                  perf0: float,
                  perfN: float,
                  normalize: bool,
                  normalize_method: str):
    r"""
    Calculate swarm robustness to fluctuating swarm populations. Equation taken from
    :xref:`Harwell2020`.

    .. math::
       B_{sz}(\kappa) = \sum_{t\in{T}}\theta_{B_{sz}}

    or

    .. math::
       B_{sz}(\kappa) = \sum_{t\in{T}}\frac{1}{1+e^(-\theta_{B_{sz}})} - \frac{1}{1+e^(+\theta_{B_{sz}})}

    depending on normalization configuration.

    where

    .. math::
       \theta_{B_{sz}}(\kappa,t) = P(N,\kappa,t) - \frac{T_S}{T}P_{ideal}(N,\kappa,t)

    """
    scaled_perf0 = float(TS) / float(T) * perf0
    theta = (perfN - scaled_perf0)

    if normalize:
        if normalize_method == 'sigmoid':
            return core.utils.Sigmoid(theta)() - core.utils.Sigmoid(-theta)()
        else:
            return None
    else:
        return theta


__api__ = [
    'RobustnessSAAUnivar',
    'RobustnessPDUnivar',
    'RobustnessSAABivar',
    'RobustnessPDBivar',
]
