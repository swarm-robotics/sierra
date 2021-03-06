# Copyright 2020 John Harwell, All rights reserved.
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

# 3rd party packages

# Project packages
from core.graphs.heatmap import HeatmapSet
import core.utils
import core.config


class IntraExpModel2DGraphSet():
    """
    Generates 4 :class:`~core.graphs.heatmap.Heatmap` plots:

    - One for the empirical data
    - One for the stddev of the empirical data
    - One for the model prediction
    - One for the difference between the model and the empirical data
    """
    @staticmethod
    def model_exists(exp_model_root: str, target_stem: str):
        return os.path.exists(os.path.join(exp_model_root, target_stem + '.model'))

    def __init__(self,
                 exp_avgd_root: str,
                 exp_model_root: str,
                 exp_graph_root: str,
                 target_stem: str,
                 target_title: str,
                 **kwargs):
        self.exp_avgd_root = exp_avgd_root
        self.exp_model_root = exp_model_root
        self.exp_graph_root = exp_graph_root
        self.target_stem = target_stem
        self.target_title = target_title
        self.kwargs = kwargs

    def generate(self):
        data_ipath = os.path.join(self.exp_avgd_root,
                                  self.target_stem + '.csv')
        data_opath = os.path.join(self.exp_graph_root,
                                  self.target_stem + '-HM' + core.config.kImageExt)
        stddev_ipath = os.path.join(self.exp_avgd_root,
                                    self.target_stem + '.stddev')
        stddev_opath = os.path.join(self.exp_graph_root,
                                    self.target_stem + '-HM-stddev' + core.config.kImageExt)

        model_ipath = os.path.join(self.exp_model_root,
                                   self.target_stem + '.model')
        model_opath = os.path.join(self.exp_graph_root,
                                   self.target_stem + '-HM-model' + core.config.kImageExt)

        model_error_ipath = os.path.join(self.exp_model_root,
                                         self.target_stem + '-HM-model-error.csv')
        model_error_opath = os.path.join(self.exp_graph_root,
                                         self.target_stem + '-HM-model-error' + core.config.kImageExt)

        # Write the error .csv to the filesystem
        data_df = core.utils.pd_csv_read(data_ipath)
        model_df = core.utils.pd_csv_read(model_ipath)
        core.utils.pd_csv_write(model_df - data_df, model_error_ipath, index=False)

        HeatmapSet(ipaths=[data_ipath, stddev_ipath, model_ipath, model_error_ipath],
                   opaths=[data_opath, stddev_opath, model_opath, model_error_opath],
                   titles=[self.target_title,
                           self.target_title + ' (Stddev)',
                           self.target_title + ' (Model)',
                           self.target_title + ' (Model Error)'],
                   xlabel='X',
                   ylabel='Y',
                   **self.kwargs).generate()
