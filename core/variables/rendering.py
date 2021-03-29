# Copyright 2021 John Harwell, All rights reserved.
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
# You should have received a copy of the GNU General Public License along with
#  SIERRA.  If not, see <http://www.gnu.org/licenses/

"""
ARGoS headless QT rendering configuration.
"""

# Core packages
import typing as tp

# 3rd party packages
import implements

# Project packages
from core.variables.base_variable import IBaseVariable
from core.utils import ArenaExtent
import core.variables.time_setup as ts
from core.xml_luigi import XMLAttrChangeSet, XMLTagRmList, XMLTagAddList, XMLTagRm, XMLTagAdd, XMLAttrChange
import core.config


@implements.implements(IBaseVariable)
class ARGoSQTHeadlessRendering():
    """
    Sets up ARGoS headless rendering with QT.

    Attributes:
        tsetup: Simulation time definitions.
        extents: List of (X,Y,Zs) tuple of dimensions of area to assign to engines of the specified
                 type.
    """

    kFrameSize = "1600x1200"
    kQUALITY = 100
    kFRAME_RATE = 10

    def __init__(self, tsetup: ts.ARGoSTimeSetup) -> None:
        self.tsetup = tsetup
        self.tag_adds = []  # type: tp.List[XMLTagAddList]

    def gen_attr_changelist(self) -> tp.List[XMLAttrChangeSet]:
        """
        Does nothing because all tags/attributes are either deleted or added.
        """
        return []

    def gen_tag_rmlist(self) -> tp.List[XMLTagRmList]:
        """
        Removing the ``<qt_opengl>`` tag if it exists may be desirable so an option is provided
        to do so. Obviously you *must* call this function BEFORE adding new definitions.

        """
        return [XMLTagRmList(XMLTagRm("./visualization", "qt-opengl"))]

    def gen_tag_addlist(self) -> tp.List[XMLTagAddList]:
        if not self.tag_adds:
            self.tag_adds = [XMLTagAddList(XMLTagAdd('.', 'visualization', {}),
                                           XMLTagAdd('./visualization',
                                                     'qt-opengl',
                                                     {'autoplay': "true"}
                                                     ),
                                           XMLTagAdd('./visualization/qt-opengl',
                                                     'frame_grabbing',
                                                     {
                                                         'directory': 'frames',
                                                         'base_name': 'frame_',
                                                         'format': core.config.kImageExt[1:],
                                                         'headless_grabbing': "true",
                                                         'headless_frame_size': "{0}".format(self.kFrameSize),
                                                         'headless_frame_rate': "{0}".format(self.kFRAME_RATE),
                                                     }),
                                           XMLTagAdd('visualization/qt-opengl',
                                                     'user_functions',
                                                     {'label': '__empty__'}))]

        return self.tag_adds


def factory(cmdopts: tp.Dict[str, tp.Any]) -> ARGoSQTHeadlessRendering:
    """
    Setups up ARGoS QT headless rendering for a the specified simulation duration.
    """

    return ARGoSQTHeadlessRendering(ts.factory(cmdopts["time_setup"])())  # type: ignore


__api__ = [
    'CameraTimeline',


]
