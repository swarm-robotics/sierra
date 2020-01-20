# Copyright 2019 John Harwell, All rights reserved.
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
Classes for averaging (1) all simulations within an experiment, (2) all experiments in a batched
experiment.
"""

import os
import re
import logging
import multiprocessing as mp
import typing as tp

import pandas as pd


class BatchedExpCSVAverager:
    """
    Averages the .csv output files for each experiment in the specified batch directory in sequence.
    """

    def __call__(self, main_config: dict, avg_opts: tp.Dict[str, str], batch_output_root: str):
        """
        Arguments:
            main_config: Parsed dictionary of main YAML configuration.
            avg_opts: Dictionary of parameters for batch averaging.
            batch_output_root: Directory for averaged .csv output (relative to current dir or
                               absolute).
        """

        # Ignore the folder for .csv files collated across experiments within a batch
        experiments = [item for item in os.listdir(batch_output_root) if item not in [
            main_config['sierra']['collate_csv_leaf']]]

        q = mp.JoinableQueue()

        for exp in experiments:
            path = os.path.join(batch_output_root, exp)
            if os.path.isdir(path):
                q.put(path)

        for i in range(0, mp.cpu_count()):
            p = mp.Process(target=BatchedExpCSVAverager.__thread_worker,
                           args=(q, main_config, avg_opts))
            p.start()

        q.join()

    @staticmethod
    def __thread_worker(q: mp.Queue, main_config: dict, avg_opts: tp.Dict[str, str]):
        while True:
            path = q.get()
            ExpCSVAverager(main_config, avg_opts, path)()
            q.task_done()


class ExpCSVAverager:
    """
    Averages a set of .csv output files from a set of simulation runs for a single experiment.

    Attributes:
        main_config: Parsed dictionary of main YAML configuration.
        template_input_leaf: Leaf(i.e. no preceding path to the template XML configuration file
                                  for the experiment.
        no_verify: Should result verification be skipped?
        gen_stddev: Should standard deviation be generated(and therefore errorbars
                    plotted)?
        exp_output_root: Directory for averaged .csv output(relative to current dir or
                         absolute).
    """

    def __init__(self, main_config: dict, avg_opts: tp.Dict[str, str], exp_output_root: str):
        self.avg_opts = avg_opts

        # will get the main name and extension of the config file (without the full absolute path)
        self.template_input_fname, _ = os.path.splitext(
            os.path.basename(self.avg_opts['template_input_leaf']))

        self.exp_output_root = os.path.abspath(exp_output_root)

        self.avgd_output_leaf = main_config['sierra']['avg_output_leaf']
        self.avgd_output_root = os.path.join(self.exp_output_root,
                                             self.avgd_output_leaf)
        self.metrics_leaf = main_config['sim']['metrics_leaf']

        os.makedirs(self.avgd_output_root, exist_ok=True)

        # to be formatted like: self.input_name_format.format(name, experiment_number)
        format_base = "{}_{}"
        self.output_name_format = format_base + "_output"

    def __call__(self):
        if not self.avg_opts['no_verify_results']:
            self.__verify_exp()
        self.__average_csvs()

    def __average_csvs(self):
        """Averages the CSV files found in the output save path"""

        logging.info('Averaging results in %s...', self.exp_output_root)

        # Maps unique .csv stem to the averaged dataframe
        csvs = {}

        pattern = self.output_name_format.format(
            re.escape(self.avg_opts['template_input_leaf']), r'\d+')

        # check to make sure all directories are simulation runs, skipping the directory within each
        # experiment that the averaged data is placed in
        experiments = [e for e in os.listdir(self.exp_output_root) if e not in [
            self.avgd_output_leaf]]

        assert(all(re.match(pattern, exp) for exp in experiments)),\
            "FATAL: Not all directories in {0} are simulation runs".format(self.exp_output_root)

        for exp in experiments:

            csv_root = os.path.join(self.exp_output_root, exp, self.metrics_leaf)
            # Nothing but .csv files should be in the metrics folder
            for csv_fname in os.listdir(csv_root):
                df = pd.read_csv(os.path.join(csv_root, csv_fname), index_col=False, sep=';')
                if csv_fname not in csvs:
                    csvs[csv_fname] = []

                csvs[csv_fname].append(df)

            # All CSV files with the same base name will be averaged together
            for csv_fname in csvs:
                csv_concat = pd.concat(csvs[csv_fname])
                by_row_index = csv_concat.groupby(csv_concat.index)
                csv_averaged = by_row_index.mean()
                csv_averaged.to_csv(os.path.join(self.avgd_output_root, csv_fname),
                                    sep=';',
                                    index=False)
                # Also write out stddev in order to calculate confidence intervals later
                if self.avg_opts['gen_stddev']:
                    csv_stddev = by_row_index.std().round(2)
                    csv_stddev_fname = csv_fname.split('.')[0] + '.stddev'
                    csv_stddev.to_csv(os.path.join(self.avgd_output_root, csv_stddev_fname),
                                      sep=';',
                                      index=False)

    def __verify_exp(self):
        """
        Verify the integrity of all simulations in an experiment.

        Specifically:

        - All simulations produced all ``.csv`` files
        - All simulation ``.csv`` files have the same # rows/columns
        - No simulation ``.csv``files contain NaNs.
        """
        experiments = [exp for exp in os.listdir(self.exp_output_root) if exp not in [
            self.avgd_output_leaf]]

        logging.info('Verifying results in %s...', self.exp_output_root)

        for exp1 in experiments:
            csv_root1 = os.path.join(self.exp_output_root,
                                     exp1,
                                     self.metrics_leaf)

            for exp2 in experiments:
                csv_root2 = os.path.join(self.exp_output_root,
                                         exp2,
                                         self.metrics_leaf)

                if not os.path.isdir(csv_root2):
                    continue

                for csv in os.listdir(csv_root2):
                    path1 = os.path.join(csv_root1, csv)
                    path2 = os.path.join(csv_root2, csv)
                    assert (os.path.exists(path1) and os.path.exists(path2)),\
                        "FATAL: Either {0} or {1} does not exist".format(path1, path2)

                    # Verify both dataframes have same # columns, and that column sets are identical
                    df1 = pd.read_csv(path1, sep=';')
                    df2 = pd.read_csv(path2, sep=';')
                    assert (len(df1.columns) == len(df2.columns)), \
                        "FATAL: Dataframes from {0} and {1} do not have same # columns".format(
                            path1, path2)
                    assert(sorted(df1.columns) == sorted(df2.columns)),\
                        "FATAL: Columns from {0} and {1} not identical".format(path1, path2)

                    # Verify the length of all columns in both dataframes is the same
                    for c1 in df1.columns:
                        assert(all(len(df1[c1]) == len(df1[c2])) for c2 in df1.columns),\
                            "FATAL: Not all columns from {0} have same length".format(path1)
                        assert(all(len(df1[c1]) == len(df2[c2])) for c2 in df1.columns),\
                            "FATAL: Not all columns from {0} and {1} have same length".format(path1,
                                                                                              path2)