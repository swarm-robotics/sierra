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

"""
Time Setup Definition:

    T{duration}[N{# datapoints per simulation}

    duration = Duration of simulation in seconds
    # datapoints per simulation = # rows in each .csv for all metrics (i.e. the granularity)

Examples:

    ``T1000``: Simulation will be 1000 seconds long, default (50) # datapoints.
    ``T2000N100``: Simulation will be 2000 seconds long, 100 datapoints (1 every 20 seconds).
"""

import typing as tp

from core.variables.base_variable import BaseVariable

"""
Default # datapoints in each .csv.
"""
kDATA_POINTS = 50

"""
Default # times each controller will be run per second in simulation.
"""
kTICKS_PER_SECOND = 5


class TimeSetup(BaseVariable):
    """
    Defines the simulation duration, metric collection interval.

    Attributes:
        sim_duration: The simulation duration in seconds, NOT timesteps.
        metric_interval: Interval for metric collection.
    """

    def __init__(self, sim_duration: int, metric_interval: int):
        self.sim_duration = sim_duration
        self.metric_interval = metric_interval

    def gen_attr_changelist(self):
        return [set([
            (".//experiment", "length", "{0}".format(self.sim_duration)),
            (".//experiment", "ticks_per_second", "{0}".format(kTICKS_PER_SECOND)),
            (".//output/metrics", "output_interval", "{0}".format(self.metric_interval))])]

    def gen_tag_rmlist(self):
        return []

    def gen_tag_addlist(self):
        return []


class TInterval(TimeSetup):
    def __init__(self):
        super().__init__(1000 / kTICKS_PER_SECOND, 1000 / kDATA_POINTS)


class TimeSetupParser():
    """
    Enforces the cmdline definition of time setup criteria.
    """

    def __call__(self, time_str: str) -> tp.Dict[str, str]:
        ret = {}

        ret.update(TimeSetupParser.duration_parse(time_str))
        ret.update(TimeSetupParser.n_datapoints_parse(time_str))
        return ret

    @staticmethod
    def duration_parse(time_str: str):
        """
        Parse the simulation duration.
        """
        ret = {}

        if "N" in time_str:
            ret["sim_duration"] = int(time_str.split("N")[0][1:])
        else:
            ret["sim_duration"] = int(time_str[1:])
        return ret

    @staticmethod
    def n_datapoints_parse(time_str: str):
        """
        Parse the  # datapoints that will be present in each .csv.
        """
        ret = {}
        if "N" in time_str:
            ret["n_datapoints"] = int(time_str.split("N")[1])
        else:
            ret["n_datapoints"] = kDATA_POINTS
        return ret


def factory(time_str: str):
    """
    Factory to create :class:`TimeSetup` derived classes from the command line definition.
    """
    attr = TimeSetupParser()(time_str.split(".")[1])

    def __init__(self):
        TimeSetup.__init__(self,
                           attr["sim_duration"],
                           attr["sim_duration"] * kTICKS_PER_SECOND / attr["n_datapoints"])

    return type(time_str,
                (TimeSetup,),
                {"__init__": __init__})