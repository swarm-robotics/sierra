# Copyright 2018 London Lowmanstone, John Harwell, All rights reserved.
#
#  This file is part of SIERRA.
#
#  SIERRA is free software: you can redistribute it and/or modify it under the terms of the GNU
#  General Public License as published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  SIERRA is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
#  A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  SIERRA.  If not, see <http://www.gnu.org/licenses/
#
"""
Core command line parsing and validation classes.
"""

import argparse
import typing as tp


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    """
    Formatter to get (somewhat) better text wrapping of arguments with --help in the terminal.
    """


class BootstrapCmdline:
    """
    Defines the cmdline arguments that are used to bootstrap SIERRA. That is, the arguments that are
    needed to load the project plugin.
    """

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(prog='sierra',
                                              formatter_class=HelpFormatter)

        self.parser.add_argument("--project",
                                 help="""

                                 Specify which :term:`Project` to load.

                                 Use=stage[1,2,3,4,5].
                                 """)
        self.parser.add_argument("--log-level",
                                 choices=["INFO", "DEBUG"],
                                 help="""

                                 The level of logging to use when running SIERRA.

                                 """,
                                 default="INFO")

        self.parser.add_argument("--hpc-env",
                                 help="""

                                 The value of this argument determines if the ``--physics-n-engines`` and ``--n-sims``
                                 options will be computed/inherited from the specified HPC environment. Otherwise, they
                                 must be specified on the cmdline.

                                 Valid values can be any folder name under the ``plugins`` directory, but the ones that
                                 come with SIERRA are:

                                 - ``local`` - This directs SIERRA to run experiments on the local machine. See
                                   :ref:`ln-hpc-plugin-local` for a detailed description.

                                 - ``pbs`` - The directs SIERRA to run experiments spread across multiple allocated
                                   nodes in an HPC computing environment managed by TORQUE-PBS. See
                                   :ref:`ln-hpc-plugin-pbs` for a detailed description.

                                 - ``slurm`` - The directs SIERRA to run experiments spread across multiple allocated
                                   nodes in an HPC computing environment managed by SLURM. See
                                   :ref:`ln-hpc-plugin-slurm` for a detailed description.

                                 - ``adhoc`` - This will direct SIERRA to run experiments on an ad-hoc network of
                                   computers. See :ref:`ln-hpc-plugin-adhoc` for a detailed description.
                                 """,
                                 default='local')


class CoreCmdline:
    """
    Defines the core command line arguments for SIERRA using: class:`argparse`.

    Project plugins should inherit from this class and add to its arguments as necessary. The
    following arguments **MUST** be added (or SIERRA will probably crash):

    - ``--controller``

    Attributes:
        parser:: class: `argparse.ArgumentParser`. Holds non stage-specific arguments.
        stage1: Cmdline arguments specific to stage1.
        stage2: Cmdline arguments specific to stage2.
        stage3: Cmdline arguments specific to stage3.
        stage4: Cmdline arguments specific to stage4.
        stage5: Cmdline arguments specific to stage5.

    Define the cmdline arguments.

    Arguments:
        scaffold_only: Boolean specifying whether actual definition should take place, or if the class should only
                       perform scaffolding. Used to correctly generate sphinx docs.
    """

    def __init__(self, scaffold_only: bool = False) -> None:
        self.parser = argparse.ArgumentParser(prog='SIERRA',
                                              formatter_class=HelpFormatter)
        self.stage1 = self.parser.add_argument_group(
            'Stage1: General options for generating experiments')
        self.stage2 = self.parser.add_argument_group(
            'Stage2: General options for running experiments')
        self.stage3 = self.parser.add_argument_group(
            'Stage3: General options for eprocessing experiment results')
        self.stage4 = self.parser.add_argument_group(
            'Stage4: General options for generating graphs')
        self.stage5 = self.parser.add_argument_group(
            'Stage5: General options for controller comparison')

        if scaffold_only:
            return

        self.parser.add_argument("--template-input-file",
                                 metavar="filepath",
                                 help="""

                                 The template ``.argos`` input file for the batched experiment.

                                 """ + self.stage_usage_doc([1, 2, 3, 4]))

        self.parser.add_argument("--exp-overwrite",
                                 help="""

                                 When SIERRA calculates the batch experiment root ( or any child path in the batch
                                 experiment root) during stage{1, 2}, if the calculated path already exists it is treated
                                 as a fatal error and no modifications to the filesystem are performed. This flag
                                 overwrides the default behavior. Provided to avoid accidentally overwrite input/output
                                 files for an experiment, forcing the user to be explicit with potentially dangerous
                                 actions.

                                 """ + self.stage_usage_doc([1, 2]),
                                 action='store_true')

        self.parser.add_argument("--sierra-root",
                                 metavar="dirpath",
                                 help="""

                                 Root directory for all SIERRA generated/created files.

                                 Subdirectories for controllers, scenarios, experiment/simulation
                                 inputs/outputs will be created in this directory as needed. Can persist
                                 between invocations of SIERRA.

                                 """ + self.stage_usage_doc([1, 2, 3, 4, 5]),
                                 default="<home directory>/exp")

        self.parser.add_argument("--scenario",
                                 metavar="<block dist>.AxBxC",
                                 help="""

                                 Which scenario the swarm comprised of robots running the controller specified via
                                 ``--controller`` should be run in.

                                 A scenario is defined as: block distribution type + arena dimensions. This is somewhat
                                 tied to foraging and other similar applications for the moment, but this may be
                                 modified in a future version of SIERRA.

                                 Valid block distribution types:

                                 - ``RN`` - Random
                                 - ``SS`` - Single source
                                 - ``DS`` - Dual source
                                 - ``QS`` - Quad source
                                 - ``PL`` - Power law

                                 A,B,C are the scenario X,Y,Z dimensions respectively (which can be any postive INTEGER
                                 values). All dimensions are required. 

                                 """ + self.stage_usage_doc([1, 2, 3, 4]))

        self.parser.add_argument("--batch-criteria",
                                 metavar="[<category>.<definition>,...]",
                                 help="""

                                 Definition of criteria(s) to use to define the experiment.

                                 Specified as a list of 0 or 1 space separated strings, each with the following
                                 general structure:

                                 ``<category>.<definition>``

                                 ``<category>`` must be a filename from the ``core/variables/`` directory, and
                                 ``<definition>`` must be a parsable name (according to the requirements of the criteria
                                 defined by the parser for ``<category>``).

                                 Not all files within the ``core/variables/`` directory contain classes which can be
                                 used as top level batch criteria; see the :ref:`ln-batch-criteria` docs for the ones
                                 that can.

                                 """ + self.stage_usage_doc([1, 2, 3, 4, 5]),
                                 nargs='+',
                                 default=[])

        self.parser.add_argument("--pipeline",
                                 metavar="stages",
                                 help="""
                                 Define which stages of the experimental pipeline to run:

                                 - Stage1: Generate the experiment definition from the template input file, batch
                                   criteria, and other command line options. Part of default pipeline.

                                 - Stage2: Run the batched experiment on a previously generated experiment. Part of
                                   default pipeline.

                                 - Stage3: Post-process experimental results after running the batched experiment; some
                                   parts of this can be done in parallel. Part of default pipeline.

                                 - Stage4: Perform deliverable generation after processing results for a batched
                                   experiment, which can include shiny graphs and videos. Part of default pipeline.

                                 - Stage5: Perform graph generation for comparing controllers AFTER graph generation for
                                   batched experiments has been run. Not part of default pipeline.

                                   .. IMPORTANT:: It is assumed that if stage5 is run that the # experiments and
                                      batch criteria are the same for all controllers that will be compared. If this is
                                      not true then weird things may or may not happen. Some level of checking and
                                      verification is performed prior to comparison, but this functionality is alpha
                                      quality at best.

                                 """,
                                 type=int,
                                 nargs='*',
                                 default=[1, 2, 3, 4]
                                 )
        self.parser.add_argument("--exp-range",
                                 help="""

                                 Set the experiment numbers from the batch to run, average, generate intra-experiment
                                 graphs from, or generate inter-experiment graphs from (0 based). Specified in the form
                                 ``min_exp_num:max_exp_num``. If omitted, runs, averages, and generates intra-experiment
                                 and inter-experiment performance measure graphs for all experiments in the batch
                                 (default behavior).

                                 This is useful to re-run part of a batched experiment in HPC environments if SIERRA
                                 gets killed before it finishes running all experiments in the batch.

                                 """ + self.stage_usage_doc([2, 3, 4]))

        self.parser.add_argument("--argos-rendering",
                                 help="""

                                 Enable ARGoS built in frame capture during stage 2+SIERRA rendering of captured frames
                                 during stage 4. See :ref:`ln-usage-rendering` for full details.

                                 This option slows things down a LOT, so if you use it, ``--n-sims`` should probably be
                                 low, unless you have gobs of computing power available.
                               """ + self.stage_usage_doc([1, 4]),
                                 action='store_true')

        self.parser.add_argument("--serial-processing",
                                 help="""

                                 If TRUE, then results processing/graph generation will be performed serially, rather
                                 than using parallellism where possible.

                                 """ + self.stage_usage_doc([3, 4]),
                                 action='store_true')

        self.stage4.add_argument("--no-collate",
                                 help="""

                                 Specify that no collation of data across experiments within a batch (stage 4) or across
                                 simulations within an experiment (stage 3) should be performed. Useful if collation
                                 takes a long time and multiple types of stage 4 outputs are desired.

                                 """ + self.stage_usage_doc([3, 4]),
                                 action='store_true')

        self.init_stage1()
        self.init_stage2()
        self.init_stage3()
        self.init_stage4()
        self.init_stage5()

    def init_stage1(self) -> None:
        """
        Define cmdline arguments for stage 1.
        """
        self.stage1.add_argument("--time-setup",
                                 help="""

                                 Defines simulation length, ticks per second, number of datapoints to capture/capture
                                 interval for each simulation. See :ref:`ln-vars-ts` for a full description.

                                 """ + self.stage_usage_doc([1]),
                                 default="time_setup.T5000")

        self.stage1.add_argument("--n-sims",
                                 type=int,
                                 help="""

                                 The # of simulations that will be run and their results averaged to form the
                                 result of a single experiment within a batch.

                                 If ``--hpc-env`` is something other than ``local`` then it will be used to determine
                                 # jobs/HPC node, # physics engines/simulation, and # threads/simulation.

                                 """ + self.stage_usage_doc([1]))

        # Physics engines options
        physics = self.parser.add_argument_group('Stage1: Physics',
                                                 'Physics engine options for stage1')

        physics.add_argument("--physics-engine-type2D",
                             choices=['dynamics2d'],
                             help="""

                             The type of 2D physics engine to use for managing spatial extents within the arena,
                             choosing one of the types that ARGoS supports. The precise 2D areas (if any) within the
                             arena which the will be controlled by 2D physics engines is defined on a per `--project`
                             basis.

                             """ + self.stage_usage_doc([1]),
                             default='dynamics2d')

        physics.add_argument("--physics-engine-type3D",
                             choices=['dynamics3d'],
                             help="""

                             The type of 3D physics engine to use for managing 3D volumetric extents within the arena,
                             choosing one of the types that ARGoS supports. The precise 3D volumes (if any) within the
                             arena which the will be controlled by 3D physics engines is defined on a per `--project`
                             basis.

                             """ + self.stage_usage_doc([1]),
                             default='dynamics3d')

        physics.add_argument("--physics-n-engines",
                             choices=[1, 2, 4, 6, 8, 16, 24],
                             type=int,
                             help="""

                             # of physics engines to use during simulation (yay ARGoS!). If N > 1, the engines will be
                             tiled in a uniform grid within the arena (X and Y spacing may not be the same depending on
                             dimensions and how many engines are chosen, however), extending upward in Z to the height
                             specified by ``--scenario`` (i.e., forming a set of "silos" rather that equal volumetric
                             extents).

                             If 2D and 3D physics engines are mixed, then half of the specified # of engines will be
                             allocated among all arena extents cumulatively managed by each type of engine. For example,
                             if 4 engines are used, with 1/3 of the arena managed by 2D engines and 2/3 by 3D, then 2
                             2D engines will manage 1/3 of the arena, and 2 3D engines will manage the other 2/3 of the
                             arena.

                             If ``--hpc-env`` is something other than ``local`` then the # physics engines will be
                             computed from the HPC environment, and the cmdline value (if any) will be ignored.

                             """ + self.stage_usage_doc([1]))
        physics.add_argument("--physics-iter-per-tick",
                             type=int,
                             help="""

                             The # of iterations all physics engines should perform per tick each time the
                             controller loops are run (the # of ticks per second for controller control loops is set via
                             ``--time-setup``).

                             """ + self.stage_usage_doc([1]),
                             default=10)

        # Rendering options
        rendering = self.parser.add_argument_group('Stage1: Rendering',
                                                   'Rendering options (stage1 only)')
        rendering.add_argument("--camera-config",
                               choices=['overhead',
                                        'argos_static',
                                        'argos_dynamic',
                                        'sierra_static',
                                        'sierra_dynamic'],
                               help="""

                               Select the camera configuration for simulation. Ignored unless ``--argos-rendering`` is
                               passed. Valid values are:

                               - ``overhead`` - Use a single overhead camera at the center of the aren looking straight
                                 down at an appropriate height to see the whole arena.

                               - ``argos_static`` - Use the default ARGoS camera configuration (12 cameras), cycling
                                 through them periodically throughout simulation without interpolation.

                               - ``sierra_static`` - Use the SIERRA ARGoS camera configuration (12 cameras), cycling
                                 through them periodically throughout simulation without interpolation.

                               - ``sierra_dynamic`` - Use the SIERRA ARGoS camera configuration (12 cameras), cycling
                                 through them periodically throughout simulation with interpolation between positions.

                                 """ + self.stage_usage_doc([1]),
                               default='overhead')

        # Robot options
        robots = self.parser.add_argument_group('Stage1: Robots',
                                                'Robot options (stage1 only)')

        robots.add_argument("--with-robot-rab",
                            help="""

                            If passed, do not remove the Range and Bearing (RAB) sensor, actuator, and medium XML
                            definitions from ``--template-input-file`` before generating experimental inputs. Otherwise,
                            the following XML tags are removed if they exist:

                            - ``.//media/range_and_bearing``
                            - `.//actuators/range_and_bearing`
                            - `.//sensors/range_and_bearing`

                            """ + self.stage_usage_doc([1]),
                            action="store_true",
                            default=False)

        robots.add_argument("--with-robot-leds",
                            help="""

                            If passed, do not remove the robot LED actuator XML definitions from the
                            ``--template-input-file`` before generating experimental inputs. Otherwise, the following
                            XML tags are removed if they exist:

                            - `.//actuators/leds`
                            - `.//medium/leds`
                            - `.//sensors/colored_blob_omnidirectional_camera`

                            """ + self.stage_usage_doc([1]),
                            action="store_true",
                            default=False)

        robots.add_argument("--with-robot-battery",
                            help="""

                            If passed, do not remove the robot battery sensor XML definitions from
                            ``--template-input-file`` before generating experimental inputs. Otherwise, the following
                            XML tags are removed if they exist:

                            - `.//entity/*/battery`
                            - `.//sensors/battery`

                            """ + self.stage_usage_doc([1]),
                            action="store_true",
                            default=False)

        robots.add_argument("--n-blocks",
                            help="""

                            # blocks that should be used in the simulation (evenly split between cube and ramp). Can
                            The
                            be used to override batch criteria, or to supplement experiments that do not set it so that
                            manual modification of input file is unneccesary.

                            This option is strongly tied to foraging, and will likely be moved out of core SIERRA
                            functionality in a future version.

                            """ + self.stage_usage_doc([1]),
                            type=int,
                            default=None)

        robots.add_argument("--n-robots",
                            help="""

                            The # robots that should be used in the simulation. Can be used to override batch criteria,
                            or to supplement experiments that do not set it so that manual modification of input file is
                            unneccesary.

                            """ + self.stage_usage_doc([1]),
                            type=int,
                            default=None)

    def init_stage2(self) -> None:
        """
        Define cmdline arguments for stage 2.
        """
        self.stage2.add_argument("--exec-resume",
                                 help="""

                                 Resume a batched experiment that was killed/stopped/etc last time SIERRA was run. This
                                 maps directly to GNU parallel's ``--resume-failed`` option.

                                 """ + self.stage_usage_doc([2]),
                                 action='store_true',
                                 default=False)

        self.stage2.add_argument("--exec-sims-per-node",
                                 help="""

                                 Specify the maximum number of parallel simulations to run. By default this is computed
                                 from the selected HPC environment for maximum throughput given the desired ``--n-sims``
                                 and CPUs/allocated node. However, for some environments being able to
                                 override the computed default can be useful.

                                 """ + self.stage_usage_doc([2]),
                                 type=int,
                                 default=None)

    def init_stage3(self) -> None:
        """
        Define cmdline arguments for stage 3.
        """
        self.stage3.add_argument('--no-verify-results',
                                 help="""

                                 If passed, then the verification step will be skipped during experimental results
                                 processing, and outputs will be averaged directly. If not all the corresponding
                                 ``.csv`` files in all experiments generated the same # rows, then SIERRA will
                                 (probably) crash during experiments exist and/or have the stage4. Verification can take
                                 a long time with large # of simulations per experiment.

                                 """ + self.stage_usage_doc([3]),
                                 action='store_true',
                                 default=False)

        self.stage3.add_argument("--dist-stats",
                                 choices=['none', 'all', 'conf95', 'bw'],
                                 help="""

                                 Specify what kinds of statistics, if any, should be calculated from the distribution of
                                 experimental data for inclusion on graphs during stage 4:

                                 - ``none`` - Only calculate and show raw mean on graphs.

                                 - ``conf95`` - Calculate standard deviation of experimental distribution and show 95%%
                                   confidence interval on relevant graphs.

                                 - ``bw`` - Calculate statistics necessary to show box and whisker plots around each
                                   point in the graph. :class:`~core.graphs.summary_line_graph.SummaryLinegraph` only.

                                 - ``all`` - Generate all possible statistics, and plot all possible
                                   statistics on graphs.
                                 """
                                 +
                                 self.graphs_applicable_doc([':class:`~core.graphs.summary_line_graph.SummaryLinegraph`',
                                                             ':class:`~core.graphs.stacked_line_graph.StackedLineGraph`'])
                                 + self.stage_usage_doc([3, 4]),
                                 default='none')

        self.stage3.add_argument("--processing-mem-limit",
                                 help="""


                                 Specify, as a percent in [0,100], how much memory SIERRA should try to limit itself to using.

                                 """ + self.stage_usage_doc([3, 4]),
                                 default=90)

    def init_stage4(self) -> None:
        """
        Define cmdline arguments for stage 4.
        """
        self.stage4.add_argument("--exp-graphs",
                                 choices=['intra', 'inter', 'all', 'none'],
                                 help="""

                                 Specify which types of graphs should be generated from experimental results:

                                 - ``intra`` - Generate intra-experiment graphs from the results of a single experiment
                                   within a batch, for each experiment in the batch (this can take a long time with
                                   large batched experiments). If any intra-experiment models are defined and enabled,
                                   those are run and the results placed on appropriate graphs.

                                 - ``inter`` - Generate inter-experiment graphs _across_ the results of all experiments
                                   in a batch. These are very fast to generate, regardless of batch experiment size. If
                                   any inter-experiment models are defined and enabled, those are run and the results
                                   placed on appropriate graphs.

                                 - ``all`` - Generate all types of graphs.

                                 - ``none`` - Skip graph generation; provided to skip graph generation if video outputs
                                   are desired instead.

                                 """ + self.stage_usage_doc([4]),
                                 default='all')

        self.stage4.add_argument("--project-no-yaml-LN",
                                 help="""

                                 Specify that the intra-experiment and inter-experiment linegraphs defined in project
                                 YAML configuration should not be generated. Useful if you are working on something
                                 which results in the generation of other types of graphs, and the generation of those
                                 linegraphs is not currently needed only slows down your development cycle.

                                 Performance measure, model linegraphs are still generated, if applicable.

                                 """,
                                 action='store_true')

        self.stage4.add_argument("--project-no-yaml-HM",
                                 help="""

                                 Specify that the intra-experiment heatmaps defined in project YAML configuration should
                                 not be generated. Useful if you are working on something which results in the
                                 generation of other types of graphs, and the generation of heatmaps only slows down
                                 your development cycle.

                                 Model heatmaps are still generated, if applicable.
                                 """,
                                 action='store_true')

        # Performance measure calculation options
        pm = self.parser.add_argument_group('Stage4: PM',
                                            'Performance measure options for stage4')

        pm.add_argument("--pm-scalability-from-exp0",
                        help="""

                        If passed, then swarm scalability will be calculated based on the "speedup" achieved by a swarm
                        of size N in exp X relative to the performance in exp 0, as opposed to the performance in exp
                        X-1 (default).

                        """ + self.stage_usage_doc([4]),
                        action='store_true')

        pm.add_argument("--pm-scalability-normalize",
                        help="""

                        If passed, then swarm scalability will be normalized into [-1,1] via sigmoids (similar to other
                        performance measures), as opposed to raw values (default). This may make graphs more or less
                        readable/interpretable.

                        """ + self.stage_usage_doc([4]),
                        action='store_true')

        pm.add_argument("--pm-self-org-normalize",
                        help="""

                        If passed, then swarm self-organization calculations will be normalized into [-1,1] via sigmoids
                        (similar to other performance measures), as opposed to raw values (default). This may make
                        graphs more or less readable/interpretable.

                        """,
                        action='store_true')

        pm.add_argument("--pm-flexibility-normalize",
                        help="""

                        If passed, then swarm flexibility calculations will be normalized into [-1,1] via sigmoids
                        (similar to other performance measures), as opposed to raw values (default). This may make graphs
                        more or less readable/interpretable; without normalization, LOWER values are better.

                       """ + self.stage_usage_doc([4]),
                        action='store_true')

        pm.add_argument("--pm-robustness-normalize",
                        help="""

                        If passed, then swarm robustness calculations will be normalized into [-1,1] via sigmoids
                        (similar to other performance measures), as opposed to raw values (default). This may make
                        graphs more or less readable/interpretable.

                        """ + self.stage_usage_doc([4]),
                        action='store_true')

        pm.add_argument("--pm-all-normalize",
                        help="""

                        If passed, then swarm scalability, self-organization, flexibility, and robustness calculations
                        will be normalized into [-1,1] via sigmoids (similar to other performance measures), as opposed
                        to raw values (default). This may make graphs more or less readable/interpretable.

                        """ + self.stage_usage_doc([4]),
                        action='store_true')

        pm.add_argument("--pm-normalize-method",
                        choices=['sigmoid'],
                        help="""

                        The method to use for normalizing performance measure results,
                        where enabled:

                        - ``sigmoid`` - Use a pair of sigmoids to normalize the results into
                          [-1, 1]. Can be used with all performance measures.

                        """ + self.stage_usage_doc([4]),
                        default='sigmoid')

        # Plotting options
        plots = self.parser.add_argument_group('Stage4: Plotting',
                                               'Plotting options for stage4')

        plots.add_argument("--plot-log-xscale",
                           help="""

                           Place the set of X values used to generate intra- and inter-experiment graphs into the
                           logarithmic space. Mainly useful when the batch criteria involves large swarm sizes, so that
                           the plots are more readable.

                           """ +

                           self.graphs_applicable_doc([':class:`~core.graphs.summary_line_graph.SummaryLinegraph`']) +
                           self.bc_applicable_doc([':ref:`Population Density <ln-bc-population-density>`',
                                                   ':ref:`Population Size <ln-bc-population-size>`']) +
                           self.stage_usage_doc([4, 5]),
                           action='store_true')

        plots.add_argument("--plot-log-yscale",
                           help="""

                           Place the set of Y values used to generate intra- and inter-experiment graphs into the
                           logarithmic space. Mainly useful when the batch criteria involves large swarm sizes, so that
                           the plots are more readable.

                           """ +

                           self.graphs_applicable_doc([':class:`~core.graphs.summary_line_graph.SummaryLinegraph`',
                                                       ':class:`~core.graphs.stacked_line_graph.StackedLineGraph`']) +
                           self.bc_applicable_doc([':ref:`Population Size <ln-bc-population-size>`',
                                                   ':ref:`Population Density <ln-bc-population-density>`']) +
                           self.stage_usage_doc([4, 5]),
                           action='store_true')

        plots.add_argument("--plot-regression-lines",
                           help="""

                           For all 2D generated scatterplots, plot a linear regression line and the equation of the line
                           to the legend. """ +

                           self.graphs_applicable_doc([':class:`~core.graphs.summary_line_graph.SummaryLinegraph`']) +
                           self.bc_applicable_doc([':ref:`SAA Noise <ln-bc-saa-noise>`']) +
                           self.stage_usage_doc([4]))

        plots.add_argument("--plot-primary-axis",
                           help="""


                           This option allows you to override the primary axis, which is normally it is computed
                           based on the batch criteria.

                           For example, if the first batch criteria swarm population size, then swarm scalability
                           metrics will be calculated by COMPUTING across .csv rows and PRJECTING down the columns by
                           default, since swarm size will only vary within a row. Passing a value of 1 to this option
                           will override this calculation, which can be useful in bivariate batch criteria in which you
                           are interested in the effect of the OTHER non-size criteria on various performance measures.

                           0=rows
                           1=columns
                           """ +
                           self.graphs_applicable_doc([':class:`~core.graphs.heatmap.Heatmap`']) +
                           self.stage_usage_doc([4]),
                           default=None)

        plots.add_argument("--plot-large-text",
                           help="""

                           This option specifies that the title, X/Y axis labels/tick labels will should be larger than
                           the SIERRA default. This is useful when generating graphs suitable for two column paper
                           format where the default text size for rendered graphs will be too small to see easily. The
                           SIERRA defaults are generally fine for the one column/journal paper format.
                           """,
                           action='store_true')

        # Model options
        models = self.parser.add_argument_group('Stage4: Models',
                                                'Model options for stage4')
        models.add_argument('--models-disable',
                            help="""

                            Disables running of all models, even if they appear in the project
                            config file.

                            """,
                            action="store_true")

        # Variance curve similarity options
        vcs = self.parser.add_argument_group('Stage4: VCS',
                                             'Variance Curve Similarity options for stage4')

        vcs.add_argument("--gen-vc-plots",
                         help="""

                          Generate plots of ideal vs. observed swarm [reactivity, adaptability] for each experiment in
                          the batch.""" +
                         self.bc_applicable_doc([':ref:`Temporal Variance <ln-bc-tv>`']) +
                         self.stage_usage_doc([4]),
                         action="store_true")

        vcs.add_argument("--rperf-cs-method",
                         help="""

                         Raw Performance curve similarity method. Specify the method to use to calculate the similarity
                         between raw performance curves from non-ideal conditions and ideal conditions (exp0). """ +
                         self.cs_methods_doc() +
                         self.bc_applicable_doc([':ref:`SAA Noise <ln-bc-saa-noise>`']) +
                         self.stage_usage_doc([4]),
                         choices=["pcm", "area_between", "frechet", "dtw", "curve_length"],
                         default="dtw")
        vcs.add_argument("--envc-cs-method",
                         help="""

                         Environmental conditions curve similarity method. Specify the method to use to calculate the
                         similarity between curves of applied variance(non-ideal conditions) and ideal conditions
                         (exp0). """ +
                         self.cs_methods_doc() +
                         self.bc_applicable_doc([':ref:`Temporal Variance <ln-bc-tv>`']) +
                         self.stage_usage_doc([4]),
                         choices=["pcm", "area_between", "frechet", "dtw", "curve_length"],
                         default="dtw")

        vcs.add_argument("--reactivity-cs-method",
                         help="""

                         Reactivity calculatation curve similarity method. Specify the method to use to calculate the
                         similarity between the inverted applied variance curve for a simulation and the corrsponding
                         performance curve. """ +
                         self.cs_methods_doc() +
                         self.bc_applicable_doc([':ref:`Temporal Variance <ln-bc-tv>`']) +
                         self.stage_usage_doc([4]),
                         choices=["pcm", "area_between", "frechet", "dtw", "curve_length"],
                         default="dtw")

        vcs.add_argument("--adaptability-cs-method",
                         help="""

                         Adaptability calculatation curve similarity method. Specify the method to use to calculate the
                         similarity between the inverted applied variance curve for a simulation and the corrsponding
                         performance curve.""" +
                         self.cs_methods_doc() +
                         self.bc_applicable_doc([':ref:`Temporal Variance <ln-bc-tv>`']) +
                         self.stage_usage_doc([4]),
                         choices=["pcm", "area_between", "frechet", "dtw", "curve_length"],
                         default="dtw")

        # Rendering options
        rendering = self.parser.add_argument_group(
            'Stage4: Rendering', 'Rendering options for stage4')

        rendering.add_argument("--render-cmd-opts",
                               help="""

                               Specify the ffmpeg options to appear between the specification of the input image files
                               and the specification of the output file. The default is suitable for use with ARGoS
                               frame grabbing set to a frames size of 1600x1200 to output a reasonable quality video.

                               """ + self.stage_usage_doc([4]),
                               default="-r 10 -s:v 800x600 -c:v libx264 -crf 25 -filter:v scale=-2:956 -pix_fmt yuv420p")

        rendering.add_argument("--project-imagizing",
                               help="""

                               Enable generation of image files from ``.csv`` files captured during stage 2 and averaged
                               during stage 3 for each experiment. See :ref:`ln-usage-rendering-project-imagizing` for
                               details and restrictions.

                               .. IMPORTANT:: Averaging the image ``.csv`` files and generating the images for each
                                  experiment does not happen automatically as part of stage 3 because it can take a LONG
                                  time and is idempotent.

                               """ + self.stage_usage_doc([3, 4]),
                               action='store_true')

        rendering.add_argument("--project-rendering",
                               help="""

                               Enable generation of videos from imagized ``.csv`` files created as a result of
                               ``--project-imagizing``. See :ref:`ln-usage-rendering-project` for details.

                               .. IMPORTANT::

                                  This does not happen automatically every time as part of stage 4 because it
                                  can take a LONG time and is idempotent.

                               """ + self.stage_usage_doc([4]),
                               action='store_true')

    def init_stage5(self) -> None:
        """
        Define cmdline arguments for stage 5.
        """
        self.stage5.add_argument("--controllers-list",
                                 help="""

                                 Comma separated list of controllers to compare within `` < sierra root > ``.

                                 The first controller in this list will be used for as the controller of primary
                                 interest if ``--comparison-type`` is passed.

                                 """ + self.stage_usage_doc([5]))

        self.stage5.add_argument("--controllers-legend",
                                 help="""

                                 Comma separated list of names to use on the legend for the generated comparison graphs,
                                 specified in the same order as the `--controllers-list`..

                                 """ + self.stage_usage_doc([5],
                                                            "If omitted: the raw controller names will be used."))

        self.stage5.add_argument("--scenarios-list",
                                 help="""

                                 Comma separated list of scenarios to compare ``--controller`` across within `` < sierra
                                 root > ``.

                                 """ + self.stage_usage_doc([5]))

        self.stage5.add_argument("--scenarios-legend",
                                 help="""

                                 Comma separated list of names to use on the legend for the generated inter-scenario
                                 controller comparison graphs(if applicable), specified in the same order as the
                                 `--scenarios-list`.

                                 """ + self.stage_usage_doc([5],
                                                            "If omitted: the raw scenario names will be used."))
        self.stage5.add_argument("--scenario-comparison",
                                 help="""

                                 Perform a comparison of ``--controller`` across `--scenarios-list` (univariate batch
                                 criteria only).
                                 """ + self.stage_usage_doc([5],
                                                            "Either ``--scenario-comparison`` or ``--controller-comparison`` must be passed."),
                                 action='store_true')

        self.stage5.add_argument("--controller-comparison",
                                 help="""

                                 Perform a comparison of ``--controllers-list`` across all scenarios at least one
                                 controller has been run on..
                                 """ + self.stage_usage_doc([5],
                                                            "Either ``--scenario-comparison`` or ``--controller-comparison`` must be passed."),
                                 action='store_true')

        self.stage5.add_argument("--comparison-type",
                                 choices=['LNraw',
                                          'HMraw', 'HMdiff', 'HMscale', 'HMdiff',
                                          'SUraw', 'SUscale', 'SUdiff'],
                                 help="""

                                 Specify how controller comparisons should be performed.

                                 If the batch criteria is univariate, the options are:

                                 - ``LNraw`` - Output raw 1D performance measures using a single
                                   :class:`~core.graphs.summary_line_graph.SummaryLinegraph` for each measure, with all
                                   ``--controllers-list`` controllers shown on the same graph.

                                 If the batch criteria is bivariate, the options are:

                                 - ``LNraw`` - Output raw performance measures as a set of
                                   :class:`~core.graphs.summary_line_graph.SummaryLinegraph`, where each line graph is
                                   constructed from the i-th row/column for the 2D dataframe for the performance results
                                   for all controllers.

                                 - ``HMraw`` - Output raw 2D performance measures as a set of dual heatmaps comparing
                                   all controllers against the controller of primary interest (one per pair).

                                 - ``HMdiff`` - Subtract the performance measure of the controller of primary interest
                                   against all other controllers, pairwise, outputting one 2D heatmap per comparison.

                                 - ``HMscale`` - Scale controller performance measures against those of the controller
                                   of primary interest by dividing, outputing one 2D heatmap per comparison.

                                 - ``SUraw`` - Output raw 3D performance measures as a single, stacked 3D surface
                                   plots comparing all controllers (identical plots, but viewed from different
                                   angles).

                                 - ``SUscale`` - Scale controller performance measures against those of the controller
                                   of primary interest by dividing. This results in a single stacked 3D surface plots
                                   comparing all controllers (identical plots, but viewed from different angles).

                                 - ``SUdiff`` - Subtract the performance measure of the controller of primary interest
                                   from each controller(including the primary). This results in a set single stacked 3D
                                   surface plots comparing all controllers (identical plots, but viewed from different
                                   angles), in which the controller of primary interest forms an(X, Y) plane at Z=0.


                                 For all comparison types, ``--controllers-legend`` is used if passed for legend.

                                 """ + self.stage_usage_doc([5]))

        self.stage5.add_argument("--bc-univar",
                                 help="""

                                 Specify that the batch criteria is univariate. This cannot be deduced from the command
                                 line ``--batch-criteria`` argument in all cases because we are comparing controllers
                                 `across` scenarios, and each scenario(potentially) has a different batch criteria
                                 definition, which will result in (potentially) erroneous comparisons if we don't
                                 re-generate the batch criteria for each scenaro we compare controllers within.

                                 """ + self.stage_usage_doc([5]),
                                 action='store_true')

        self.stage5.add_argument("--bc-bivar",
                                 help="""

                                 Specify that the batch criteria is bivariate. This cannot be deduced from the command
                                 line ``--batch-criteria`` argument in all cases because we are comparing controllers
                                 `across` scenarios, and each scenario(potentially) has a different batch criteria
                                 definition, which will result in (potentially) erroneous comparisons if we don't
                                 re-generate the batch criteria for each scenaro we compare controllers in .

                                 """ + self.stage_usage_doc([5]),
                                 action='store_true')

        self.stage5.add_argument("--transpose-graphs",
                                 help="""

                                 Transpose the X, Y axes in generated graphs. Useful as a general way to tweak graphs for
                                 best use of space within a paper. Currently affects the following graphs:

                                 -: class: `~core.graphs.heatmap.Heatmap`

                                 Ignored for other graph types.

                                 """ + self.stage_usage_doc([5]),
                                 action='store_true')

    @staticmethod
    def cs_methods_doc() -> str:
        return r"""

        The following methods can be specified. Note that each some methods have a defined normalized domain, and some do
        not, and that the normalized domain may invert the meaning of lower values=better. If defined, the normalized
        domain the default for a given measure.

        - ``pcm`` - Partial Curve Mapping(Witowski2012)

          - Intrinsic domain:: math: `[0, \infty)`. Lower values indicate greater similarity.

          - Normalized domain: N/A.

        - ``area_between`` - Area between the two curves(Jekel2018)

          - Intrinsic domain::math:`[0, \infty)`. Lower values indicate greater similarity.

          - Normalized domain: N/A.

        - ``frechet`` - Frechet distance(Frechet1906)

          - Intrinsic domain::math:`[0, \infty)`. Lower values indicate greater similarity.

          - Normalized domain: N/A.

        - ``dtw`` - Dynamic Time Warping(Berndt1994)

          - Intrinsic domain::math:`[0, \infty)`. Lower values indicate greater similarity.

          - Normalized domain: [0, 1]. Higher values indicate greater similarity.

        - ``curve_length`` - Arc-length distance along the curve from the origin of(applied - ideal)
          curve(Andrade-campos2009).

          - Intrinsic domain::math:`[0, \infty)`.

          - Normalized domain: N/A.
        """

    @staticmethod
    def stage_usage_doc(stages: tp.List[int], omitted: str = "If omitted: N/A.") -> str:
        return "\n.. ADMONITION:: Stage usage\n\n   Used by stage{" + ",".join(map(str, stages)) + "}; can be omitted otherwise. " + omitted + "\n"

    @staticmethod
    def bc_applicable_doc(criteria: tp.List[str]) -> str:
        lst = "".join(map(lambda bc: "   - " + bc + "\n", criteria))
        return "\n.. ADMONITION:: Applicable batch criteria\n\n" + lst + "\n"

    @staticmethod
    def graphs_applicable_doc(graphs: tp.List[str]) -> str:
        lst = "".join(map(lambda graph: "   - " + graph + "\n", graphs))
        return "\n.. ADMONITION:: Applicable graphs\n\n" + lst + "\n"


class CoreCmdlineValidator():
    """
    Validate the core command line arguments to ensure that the pipeline will work properly in all
    stages, given the options that were passed.
    """

    def __call__(self, args) -> None:
        assert len(args.batch_criteria) <= 2, "FATAL: Too many batch criteria passed"

        assert args.sierra_root is not None, '--sierra-root is required for all stages'

        if len(args.batch_criteria) == 2:
            assert args.batch_criteria[0] != args.batch_criteria[1], \
                "FATAL: Duplicate batch criteria passed"

        assert isinstance(args.batch_criteria, list), \
            'FATAL Batch criteria not passed as list on cmdline'

        if any([1]) in args.pipeline:
            assert args.n_sims is not None, '--n-sims is required for running stage 1'
            assert args.template_input_file is not None, '--template-input-file is required for running stage 1'
            assert args.scenario is not None, '--scenario is required for running stage 1'

        if any([1, 2, 3, 4]) in args.pipeline:
            assert len(args.batch_criteria) > 0, '--batch-criteria is required for running stages 1-4'
            assert args.controller is not None, '--controller is required for running stages 1-4'

        if 5 in args.pipeline:
            assert args.bc_univar or args.bc_bivar, \
                '--bc-univar or --bc-bivar is required for stage 5'
            assert args.scenario_comparison or args.controller_comparison,\
                '--scenario-comparison or --controller-comparison required for stage 5'


def sphinx_cmdline_core() -> argparse.ArgumentParser:
    """
    Return a handle to the core cmdline object for SIERRA in order for sphinx to autogenerate nice
    documentation from it.
    """
    return CoreCmdline().parser


def sphinx_cmdline_bootstrap() -> argparse.ArgumentParser:
    """
    Return a handle to the bootstrap cmdline object for SIERRA in order for sphinx to autogenerate
    nice documentation from it.
    """
    return BootstrapCmdline().parser


__api__ = [
    'BootstrapCmdline',
    'CoreCmdline',
]
