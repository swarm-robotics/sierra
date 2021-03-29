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
Classes for running and single and batched experiments via the configured method specified on
the cmdline (usually GNU parallel).
"""

# Core packages
import os
import subprocess
import time
import sys
import logging
import datetime
import typing as tp

# 3rd party packages

# Project packages
from core.variables import batch_criteria as bc
import core.hpc


class BatchedExpRunner:
    """
    Runs each experiment in the specified batch experiment directory in sequence using GNU Parallel.

    Attributes:
        batch_exp_root: Absolute path to the root directory for the batch experiment
                        (i.e. experiment directories are placed in here).
        cmdopts: Dictionary of parsed cmdline options.
        criteria: Batch criteria for the experiment.
        exec_exp_range: The subset of experiments in the batch to run (can be None to run all
                        experiments in the batch).

    """

    def __init__(self, cmdopts: tp.Dict[str, tp.Any], criteria: bc.BatchCriteria) -> None:
        self.cmdopts = cmdopts
        self.criteria = criteria

        self.batch_exp_root = os.path.abspath(self.cmdopts['batch_input_root'])
        self.batch_stat_root = os.path.abspath(self.cmdopts['batch_stat_root'])
        self.batch_stat_exec_root = os.path.join(self.batch_stat_root, 'exec')
        self.exec_exp_range = self.cmdopts['exp_range']

        self.logger = logging.getLogger(__name__)

        core.utils.dir_create_checked(self.batch_stat_exec_root, exist_ok=True)

    def __call__(self) -> None:
        """
        Runs experiments in the batch according to configuration.

        Arguments:
            n_threads_per_sim: How many threads each ARGoS simulation will use. Not used in this
                               function except as diagnostic output (setting # threads used is done
                               in stage1).
            n_sims: How many ARGoS simulations will be run for each experiment. Not used in this
                    function except as diagnostic output (setting # simulations used is done in
                    stage1).
            exec_resume: Is this run of SIERRA resuming a previous run that failed/did not finish?

            with_rendering: Is ARGoS headless rendering enabled? If so, we will need to kill all the
                            Xvfb processes that get run for each simulation after all experiments
                            are finished.
        """
        n_threads_per_sim = self.cmdopts['physics_n_engines']
        n_sims = self.cmdopts['n_sims']
        exec_resume = self.cmdopts['exec_resume']
        with_rendering = self.cmdopts['argos_rendering']
        n_jobs = self.cmdopts['exec_sims_per_node']

        now = datetime.datetime.now()
        exec_times_fpath = os.path.join(self.batch_stat_exec_root,
                                        now.strftime("%Y-%m-%e-%H:%M"))

        s = "Running batched experiment in '%s': sims_per_exp=%s,threads_per_sim=%s,n_jobs=%s"
        self.logger.info(s, self.cmdopts['batch_root'], n_sims, n_threads_per_sim, n_jobs)

        exp_all = [os.path.join(self.batch_exp_root, d)
                   for d in self.criteria.gen_exp_dirnames(self.cmdopts)]

        exp_to_run = core.utils.exp_range_calc(self.cmdopts, self.batch_exp_root, self.criteria)

        # Verify environment is OK before running anything
        core.hpc.EnvChecker()

        for exp in exp_to_run:
            runner = ExpRunner(exp, exp_all.index(exp), self.cmdopts['hpc_env'], exec_times_fpath)
            runner(n_jobs, exec_resume)

        # Cleanup Xvfb processes which were started in the background
        if with_rendering:
            subprocess.run(['killall', 'Xvfb'], check=True)


class ExpRunner:
    """
    Runs the specified  # of simulations in parallel using GNU Parallel on a provided set of hosts
    in an HPC environment, or on the current local machine.

    Attributes:
        exp_input_root: Absolute path to the root directory for all generated simulation
                             input files for the experiment (i.e. an experiment directory
                             within the batch experiment root).
        exp_num: Experiment number in the batch.

    """

    def __init__(self,
                 exp_input_root: str,
                 exp_num: int,
                 hpc_env: str,
                 exec_times_fpath: str) -> None:
        self.exp_input_root = os.path.abspath(exp_input_root)
        self.exp_num = exp_num
        self.hpc_env = hpc_env
        self.exec_times_fpath = exec_times_fpath
        self.logger = logging.getLogger(__name__)

    def __call__(self, n_jobs: int, exec_resume: bool) -> None:
        """
        Runs the simulations for a single experiment in parallel.

        Arguments:
            n_jobs: How many concurrent jobs are allowed? (Don't want
                    to oversubscribe the machine).
            exec_resume: Is this run of SIERRA resuming a previous run that failed/did not finish?

        """

        self.logger.info("Running exp%s in '%s'", self.exp_num, self.exp_input_root)
        sys.stdout.flush()

        start = time.time()
        parallel_opts = {
            # Root directory for the job. Chose the exp input directory rather than the output
            # directory in order to keep simulation outputs separate from those for the framework
            # used to run the experiments.
            'jobroot_path': self.exp_input_root,
            'cmdfile_path': os.path.join(self.exp_input_root, "commands.txt"),
            'joblog_path': os.path.join(self.exp_input_root, "parallel.log"),
            'exec_resume': exec_resume,
            'n_jobs': n_jobs
        }
        try:
            cmd = core.hpc.GNUParallelCmdGenerator()(self.hpc_env, parallel_opts)
            subprocess.run(cmd, shell=True, check=True)

        # Catch the exception but do not raise it again so that additional experiments can still be
        # run if possible
        except subprocess.CalledProcessError as e:
            self.logger.error("Experiment failed! rc=%s", e.returncode)
            self.logger.error("Check outputs in %s for details", parallel_opts['jobroot_path'])

        elapsed = int(time.time() - start)
        sec = datetime.timedelta(seconds=elapsed)
        self.logger.info('Exp%s elapsed time: %s', self.exp_num, str(sec))

        with open(self.exec_times_fpath, 'a') as f:
            f.write('exp' + str(self.exp_num) + ': ' + str(sec) + '\n')
