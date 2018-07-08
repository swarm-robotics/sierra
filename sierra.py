"""
Copyright 2018 London Lowmanstone, John Harwell, All rights reserved.

  This file is part of SIERRA.

  SIERRA is free software: you can redistribute it and/or modify it under the terms of the GNU
  General Public License as published by the Free Software Foundation, either version 3 of the
  License, or (at your option) any later version.

  SIERRA is distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
  A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with
  SIERRA.  If not, see <http://www.gnu.org/licenses/

"""

import argparse
import os
from exp_pipeline import ExpPipeline
from batched_exp_input_generator import BatchedExpInputGenerator


def get_input_generator(args):
    """Get the input generator to use to create experiment/batch inputs."""
    if not any([args.graphs_only, args.run_only, args.average_only]):
        exp = __import__(
            str("experiments." + args.exp_type), fromlist=["*"])

        if args.batch:
            criteria = __import__("batch_criteria.{0}".format(
                args.batch_criteria.split(".")[0]), fromlist=["*"])
            return BatchedExpInputGenerator(args.template_config_file,
                                            args.generation_root,
                                            args.output_root,
                                            getattr(criteria, args.batch_criteria.split(
                                                ".")[1])().gen_list(),
                                            getattr(exp, "BaseInputGenerator"),
                                            args.n_sims,
                                            args.n_threads,
                                            args.random_seed_min,
                                            args.random_seed_max)
        else:
            return getattr(exp, "BaseInputGenerator")(args.template_config_file,
                                                      args.generation_root,
                                                      args.output_root,
                                                      args.n_sims,
                                                      args.n_threads,
                                                      args.random_seed_min,
                                                      args.random_seed_max)


def define_cmdline():
    """Define the command line arguments for sierra. Returns a parser with the definitions."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--template-config-file",
                        help="The template configuration file for the experiment.")

    parser.add_argument("--n_sims",
                        help="How many simulations to run in a single experiment in parallel. Defaults to 100.", type=int, default=100)
    parser.add_argument("--generation-root",
                        help="Root directory to save generated files. Defaults to ~/generated-inputs.",
                        default=os.path.expanduser("~/generated-inputs"))
    parser.add_argument("--n_threads",
                        help="How many ARGoS simulation threads to use. Defaults to 4.",
                        type=int,
                        default=4)

    # upgrade: think about adding a save CSV path
    parser.add_argument("--output-root",
                        help="Root directory for saving simulation outputs (sort of a scratch dir). Defaults to ~/output",
                        default=os.path.expanduser("~/output"))
    parser.add_argument("--graph-root",
                        help="Root directory for saving generated graph files. Defaults to ~/generated-graphs.",
                        default=os.path.expanduser("~/generated-graphs"))

    run_group = parser.add_mutually_exclusive_group()
    run_group.add_argument("--inputs-only",
                           help="Only generate the config files and command file for an experiment/set of experiments.",
                           action="store_true")
    run_group.add_argument("--run-only",
                           help="Only run the experiments on previously generated set of input files for an experiment/set of experiments.",
                           action="store_true")
    run_group.add_argument("--average-only",
                           help="Only perform CSV averaging on a previously run experiment/set of experiments.",
                           action="store_true")
    run_group.add_argument("--graphs-only",
                           help="Only perform graph generation on a previous run experiments/set of experiments.",
                           action="store_true")
    parser.add_argument("--exp_type",
                        help="Experiment to run. Options are: [stateless, stateful]")

    parser.add_argument("--no-msi",
                        help="Include if running on a personal computer (otherwise runs supercomputer commands).",
                        action="store_true")

    parser.add_argument("--random-seed-min",
                        help="The minimum random seed number", type=int)
    parser.add_argument("--random-seed-max",
                        help="The maximum random seed number", type=int)

    parser.add_argument("--batch",
                        help="Run a batch of experiments instead of a single one.",
                        action="store_true")
    parser.add_argument("--batch-criteria",
                        help='''\
                        Name of criteria to use to generate the batched experiments. Options are:
                        swarm_size.Linear<X> (<X> = 64...1024 by powers of 2),
                        swarm_size.Log<X> (<X> = 64...1024 by powers of 2),
                        arena_size.RectangularArenaTwoByOne (X=10...100 by 10s, Y=5...50 by 5s),
                        arena_size.RectangularArenaCorridor (X=10...100 by 10s, Y=5),
                        task_allocation.EstimationAlpha (Alpha=0.1...0.9)''')
    return parser


if __name__ == "__main__":
    # check python version
    import sys
    if sys.version_info < (3, 0):
        # restriction: cannot use Python 2.x to run this code
        raise RuntimeError("Python 3.x should must be used to run this code.")

    parser = define_cmdline()
    args = parser.parse_args()

    pipeline = ExpPipeline(args, get_input_generator(args))
    pipeline.run()