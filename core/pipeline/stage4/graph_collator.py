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


# Core packages
import os
import logging
import multiprocessing as mp
import queue
import typing as tp

# 3rd party packages
import pandas as pd

# Project packages
import core.utils
import core.config


class UnivarGraphCollationInfo():
    """
    Data class containing the collated ``.csv`` files for a particular graph for univariate batch
    criteria.
    """

    def __init__(self,
                 df_ext: str,
                 ylabels: tp.List[str]) -> None:
        self.df_ext = df_ext
        self.df = pd.DataFrame(columns=ylabels)
        self.all_srcs_exist = True
        self.some_srcs_exist = False
        self.is_pickle = False


class BivarGraphCollationInfo():
    """
    Data class containing the collated ``.csv`` files for a particular graph for bivariate batch
    criteria.
    """

    def __init__(self,
                 df_ext: str,
                 xlabels: tp.List[str],
                 ylabels: tp.List[str]) -> None:
        self.df_ext = df_ext
        self.df = pd.DataFrame(columns=ylabels, index=xlabels)
        self.all_srcs_exist = True
        self.some_srcs_exist = False


class UnivarGraphCollator:
    """
    For a single graph (target) in a univariate batched experiment, go through all experiment
    directories in a batched experiment and collate file averaged results into a single ``.csv``
    file.
    """

    def __init__(self, main_config: dict, cmdopts: dict) -> None:
        self.main_config = main_config
        self.cmdopts = cmdopts
        self.logger = logging.getLogger(__name__)

    def __call__(self, criteria, target: dict, stat_collate_root: str) -> None:
        self.logger.info("Stage4: Collating univariate files from batch in %s for graph '%s'...",
                         self.cmdopts['batch_output_root'],
                         target['src_stem'])

        exp_dirs = core.utils.exp_range_calc(self.cmdopts,
                                             self.cmdopts['batch_output_root'],
                                             criteria)

        stats = [UnivarGraphCollationInfo(df_ext=core.config.kStatsExtensions[ext],
                                          ylabels=[os.path.split(e)[1] for e in exp_dirs])
                 for ext in core.config.kStatsExtensions.keys()]

        for i, diri in enumerate(exp_dirs):
            # We get full paths back from the exp dirs calculation, and we need to work with path
            # leaves
            diri = os.path.split(diri)[1]
            self._collate_exp(target, diri, stats)

        for stat in stats:
            if stat.all_srcs_exist:
                if not stat.is_pickle:
                    core.utils.pd_csv_write(stat.df, os.path.join(stat_collate_root,
                                                                  target['dest_stem'] + stat.df_ext),
                                            index=False)
                else:
                    core.utils.pd_pickle_write(stat.df,
                                               os.path.join(stat_collate_root,
                                                            target['dest_stem'] + stat.df_ext))
            elif not stat.all_srcs_exist and stat.some_srcs_exist:
                self.logger.warning("Not all experiments in '%s' produced '%s%s'",
                                    self.cmdopts['batch_output_root'],
                                    target['src_stem'],
                                    stat.df_ext)

    def _collate_exp(self, target: dict, exp_dir: str, stats: tp.List[UnivarGraphCollationInfo]) -> None:
        exp_stat_root = os.path.join(self.cmdopts['batch_stat_root'], exp_dir)

        for stat in stats:
            csv_ipath = os.path.join(exp_stat_root, target['src_stem'] + stat.df_ext)
            if not core.utils.path_exists(csv_ipath):
                stat.all_srcs_exist = False
                continue

            stat.some_srcs_exist = True

            if core.config.kPickleExt not in csv_ipath:
                data_df = core.utils.pd_csv_read(csv_ipath)
            else:
                stat.is_pickle = True
                data_df = core.utils.pd_pickle_read(csv_ipath)

            assert target['col'] in data_df.columns.values,\
                "FATAL: {0} not in columns of {1}".format(target['col'],
                                                          target['src_stem'] + stat.df_ext)

            if target.get('summary', False):
                stat.df.loc[0, exp_dir] = data_df.loc[data_df.index[-1], target['col']]
            else:
                stat.df[exp_dir] = data_df[target['col']]


class BivarGraphCollator:
    """
    For a single graph (target) for a bivariate batched experiment, go through all experiment
    directories in a batched experiment and collate file averaged results into a single ``.csv``
    file.

    """

    def __init__(self, main_config: dict, cmdopts: dict) -> None:
        self.main_config = main_config
        self.cmdopts = cmdopts
        self.logger = logging.getLogger(__name__)

    def __call__(self, criteria, target: dict, stat_collate_root: str) -> None:
        self.logger.info("Stage4: Collating bivariate files from batch in %s for graph '%s'...",
                         self.cmdopts['batch_output_root'],
                         target['src_stem'])

        exp_dirs = core.utils.exp_range_calc(self.cmdopts,
                                             self.cmdopts['batch_output_root'],
                                             criteria)

        # Because sets are used, if a sub-range of experiments are selected for collation, the
        # selected range has to be an even multiple of the # of experiments in the second batch
        # criteria, or inter-experiment graph generation won't work (the final .csv is always an MxN
        # grid).
        xlabels_set = set()
        ylabels_set = set()
        for e in exp_dirs:
            pair = os.path.split(e)[1].split('+')
            xlabels_set.add(pair[0])
            ylabels_set.add(pair[1])

        xlabels = sorted(list(xlabels_set))
        ylabels = sorted(list(ylabels_set))

        stats = [BivarGraphCollationInfo(df_ext=core.config.kStatsExtensions[ext],
                                         xlabels=xlabels,
                                         ylabels=ylabels)
                 for ext in core.config.kStatsExtensions.keys()]

        for i, diri in enumerate(exp_dirs):
            # We get full paths back from the exp dirs calculation, and we need to work with path
            # leaves
            diri = os.path.split(diri)[1]
            self._collate_exp(target, diri, stats)

        for stat in stats:
            if stat.all_srcs_exist:
                if not stat.is_pickle:
                    core.utils.pd_csv_write(stat.df, os.path.join(stat_collate_root,
                                                                  target['dest_stem'] + stat.df_ext),
                                            index=False)
                else:
                    core.utils.pd_pickle_write(stat.df, os.path.join(stat_collate_root,
                                                                     target['dest_stem'] + stat.df_ext))

            elif stat.some_srcs_exist:
                self.logger.warning("Not all experiments in '%s' produced '%s%s'",
                                    self.cmdopts['batch_output_root'],
                                    target['src_stem'],
                                    stat.df_ext)

    def _collate_exp(self,
                     target: dict,
                     exp_dir: str,
                     stats: tp.List[BivarGraphCollationInfo]) -> None:
        exp_stat_root = os.path.join(self.cmdopts['batch_stat_root'], exp_dir)

        for stat in stats:
            csv_ipath = os.path.join(exp_stat_root, target['src_stem'] + stat.df_ext)
            if not core.utils.path_exists(csv_ipath):
                stat.all_srcs_exist = False
                continue

            stat.some_srcs_exist = True

            if core.config.kPickleExt not in csv_ipath:
                data_df = core.utils.pd_csv_read(csv_ipath)
            else:
                stat.is_pickle = True
                data_df = core.utils.pd_pickle_read(csv_ipath)

            assert target['col'] in data_df.columns.values,\
                "FATAL: {0} not in columns of {1}".format(target['col'],
                                                          target['src_stem'] + stat.df_ext)
            xlabel, ylabel = exp_dir.split('+')
            stat.df.loc[xlabel, ylabel] = data_df[target['col']].to_numpy()


class MultithreadCollator():
    """
    Generates collated ``.csv`` files from the averaged ``.csv`` files present in a batch of
    experiments for univariate or bivariate batch criteria. Each collated ``.csv`` file will have
    one column per experiment, named after the experiment directory, containing a column drawn from
    a ``.csv`` in the experiment's averaged output, per graph configuration.

    """

    def __init__(self, main_config: dict, cmdopts: dict) -> None:
        self.main_config = main_config
        self.cmdopts = cmdopts

        self.batch_stat_collate_root = self.cmdopts['batch_stat_collate_root']
        core.utils.dir_create_checked(self.batch_stat_collate_root, exist_ok=True)

    def __call__(self, criteria, targets: dict) -> None:
        q = mp.JoinableQueue()  # type: mp.JoinableQueue

        # For each category of graphs we are generating
        for category in targets:
            # For each graph in each category
            for graph in category['graphs']:
                q.put(graph)

        if self.cmdopts['serial_processing']:
            parallelism = 1
        else:
            parallelism = mp.cpu_count()

        for i in range(0, parallelism):
            p = mp.Process(target=MultithreadCollator._thread_worker,
                           args=(q,
                                 self.main_config,
                                 self.cmdopts,
                                 self.batch_stat_collate_root,
                                 criteria))
            p.start()

        q.join()

    @staticmethod
    def _thread_worker(q: mp.Queue,
                       main_config: dict,
                       cmdopts: dict,
                       stat_collate_root: str,
                       criteria) -> None:

        collator = None  # type: tp.Any

        if criteria.is_univar():
            collator = UnivarGraphCollator(main_config, cmdopts)
        else:
            collator = BivarGraphCollator(main_config, cmdopts)

        while True:
            # Wait for 3 seconds after the queue is empty before bailing
            try:
                graph = q.get(True, 3)
                collator(criteria, graph, stat_collate_root)
                q.task_done()
            except queue.Empty:
                break


__api__ = ['UnivarGraphCollator',
           'BivarGraphCollator',
           'UnivarGraphCollationInfo',
           'BivarGraphCollationInfo']
