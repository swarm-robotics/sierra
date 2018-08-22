"""
Copyright 2018 John Harwell, All rights reserved.

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

import os
from graphs.stacked_line_graph import StackedLineGraph


class InterExpLinegraphs:
    """
    Generates linegraphs from collated .csv data across a batch of experiments

    Attributes:
      csv_root(str): Root directory (relative to current dir or absolute) for collated csvs.
                      outputs.
      graph_root(str): Root directory (relative to current dir or absolute) of where the
                             generated graphs should be saved.
      collate_targets(list): Dictionary of lists of dictiaries specifying what graphs should be
                             generated. Passed here to reduce typing.
    """

    def __init__(self, csv_root, graph_root, collate_targets):
        self.csv_root = csv_root
        self.graph_root = graph_root
        self.collate_targets = collate_targets

    def generate(self):
        self._depth0_generate_linegraphs()
        self._depth1_generate_linegraphs()

    def _depth0_generate_linegraphs(self):
        for target_set in [self.collate_targets[x] for x in ['fsm-collision',
                                                             'fsm-movement',
                                                             'block_trans',
                                                             'block_acq',
                                                             'block_manip',
                                                             'world_model']]:
            for target in target_set:
                StackedLineGraph(input_stem_fpath=os.path.join(self.csv_root,
                                                               target['dest_stem']),
                                 output_fpath=os.path.join(
                                     self.graph_root,
                                     target['dest_stem'] + '.eps'),
                                 cols=None,
                                 title=target['title'],
                                 legend=None,
                                 xlabel=target['xlabel'],
                                 ylabel=target['ylabel']).generate()

    def _depth1_generate_linegraphs(self):
        for target_set in [self.collate_targets[x] for x in ['cache_acq',
                                                             'cache_util',
                                                             'cache_lifecycle',
                                                             'task_exec',
                                                             'generalist_tab']]:
            for target in target_set:
                StackedLineGraph(input_stem_fpath=os.path.join(self.csv_root,
                                                               target['dest_stem']),
                                 output_fpath=os.path.join(
                                     self.graph_root,
                                     target['dest_stem'] + '.eps'),
                                 cols=None,
                                 title=target['title'],
                                 legend=None,
                                 xlabel=target['xlabel'],
                                 ylabel=target['ylabel']).generate()