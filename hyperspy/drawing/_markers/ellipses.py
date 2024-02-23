# -*- coding: utf-8 -*-
# Copyright 2007-2023 The HyperSpy developers
#
# This file is part of HyperSpy.
#
# HyperSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HyperSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HyperSpy. If not, see <https://www.gnu.org/licenses/#GPL>.

from hyperspy.docstrings.markers import (
    OFFSET_DOCSTRING,
    HEIGHTS_DOCSTRING,
    WIDTHS_DOCSTRING,
    ANGLES_DOCSTRING,
    UNITS_DOCSTRING,
)

from hyperspy.drawing.markers import Markers
from hyperspy.external.matplotlib.collections import EllipseCollection


class Ellipses(Markers):
    """A set of Ellipse Markers"""

    _position_key = "offsets"

    def __init__(
        self,
        offsets,
        heights,
        widths,
        angles=0,
        offset_transform="data",
        units="xy",
        **kwargs,
    ):
        """Initialize the set of Ellipse Markers.

        Parameters
        ----------
        %s
        %s
        %s
        %s
        %s
        kwargs:
            Additional keyword arguments are passed to :class:`matplotlib.collections.EllipseCollection`.
        """
        if kwargs.setdefault("transform", "display") != "display":
            raise ValueError(
                "The transform argument is not supported for Squares Markers. Instead, "
                "use the offset_transform argument to specify the transform of the "
                "offsets and use the ``units`` argument to specify transform of the "
                "sizes."
            )
        super().__init__(
            collection=EllipseCollection,
            offsets=offsets,
            offset_transform=offset_transform,
            heights=heights,
            widths=widths,
            angles=angles,
            units=units,
            **kwargs,
        )

    __init__.__doc__ %= (
        OFFSET_DOCSTRING,
        HEIGHTS_DOCSTRING,
        WIDTHS_DOCSTRING,
        ANGLES_DOCSTRING,
        UNITS_DOCSTRING,
    )
