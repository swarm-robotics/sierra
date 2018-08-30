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
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


class Heatmap:
    """
    Generates a X vs. Y vs. Z heatmap plot.

    If the necessary .csv file does not exist, the graph is not generated.

    """

    def __init__(self, input_fpath, output_fpath, title, xlabel, ylabel):

        self.input_csv_fpath = os.path.abspath(input_fpath)
        self.output_fpath = os.path.abspath(output_fpath)
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel

    def generate(self):
        if not os.path.exists(self.input_csv_fpath):
            return

        df = pd.read_csv(self.input_csv_fpath, sep=';')
        fig, ax = plt.subplots()
        plt.imshow(df, cmap='hot', interpolation='nearest')

        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        plt.title(self.title)

        fig = ax.get_figure()
        fig.set_size_inches(10, 10)
        fig.savefig(self.output_fpath, bbox_inches='tight', dpi=100)
        fig.clf()