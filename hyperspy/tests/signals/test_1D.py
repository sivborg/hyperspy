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

import numpy as np

import pytest

from hyperspy.components1d import Gaussian
from hyperspy.decorators import lazifyTestClass
from hyperspy.signals import Signal1D


@lazifyTestClass
class Test1D:
    def setup_method(self, method):
        gaussian = Gaussian()
        gaussian.A.value = 20
        gaussian.sigma.value = 10
        gaussian.centre.value = 50
        self.signal = Signal1D(gaussian.function(np.arange(0, 100, 0.01)))
        self.signal.axes_manager[0].scale = 0.01

    @pytest.fixture
    def zero_d_navigate(self):
        return Signal1D(np.arange(0, 100, 0.01))

    @pytest.fixture
    def one_d_navigate(self):
        return Signal1D(np.repeat(np.arange(0, 100, 1)[np.newaxis, :], 3, axis=0))

    def test_integrate1D(self):
        integrated_signal = self.signal.integrate1D(axis=0)
        np.testing.assert_allclose(integrated_signal.data, 20, rtol=1e-6)
