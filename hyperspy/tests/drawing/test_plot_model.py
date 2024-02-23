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
from pathlib import Path

import hyperspy.api as hs
from hyperspy.components1d import Gaussian
from hyperspy.signals import Signal1D

my_path = Path(__file__).resolve().parent
baseline_dir = "plot_model"
default_tol = 2.0


def create_ll_signal(signal_shape=1000):
    offset = 0
    zlp_param = {"A": 10000.0, "centre": 0.0 + offset, "sigma": 15.0}
    zlp = Gaussian(**zlp_param)
    plasmon_param = {"A": 2000.0, "centre": 200.0 + offset, "sigma": 75.0}
    plasmon = Gaussian(**plasmon_param)
    axis = np.arange(signal_shape)
    data = zlp.function(axis) + plasmon.function(axis)
    ll = Signal1D(data)
    ll.axes_manager[-1].offset = -offset
    ll.axes_manager[-1].scale = 0.1
    return ll


A_value_gaussian = [1000.0, 600.0, 2000.0]
centre_value_gaussian = [50.0, 20.0, 60.0]
sigma_value_gaussian = [5.0, 3.0, 1.0]
scale = 0.1


def create_sum_of_gaussians():
    param1 = {
        "A": A_value_gaussian[0],
        "centre": centre_value_gaussian[0] / scale,
        "sigma": sigma_value_gaussian[0] / scale,
    }
    gs1 = Gaussian(**param1)
    param2 = {
        "A": A_value_gaussian[1],
        "centre": centre_value_gaussian[1] / scale,
        "sigma": sigma_value_gaussian[1] / scale,
    }
    gs2 = Gaussian(**param2)
    param3 = {
        "A": A_value_gaussian[2],
        "centre": centre_value_gaussian[2] / scale,
        "sigma": sigma_value_gaussian[2] / scale,
    }
    gs3 = Gaussian(**param3)

    axis = np.arange(1000)
    data = gs1.function(axis) + gs2.function(axis) + gs3.function(axis)

    s = Signal1D(data[:1000])
    s.axes_manager[-1].scale = scale
    return s


@pytest.mark.parametrize("binned", [True, False])
@pytest.mark.parametrize("plot_component", [True, False])
@pytest.mark.mpl_image_compare(baseline_dir=baseline_dir, tolerance=default_tol)
def test_plot_gaussian_signal1D(plot_component, binned):
    s = create_sum_of_gaussians()
    s.axes_manager[-1].is_binned == binned
    s.metadata.General.title = "plot_component: {}, binned: {}".format(
        plot_component, binned
    )

    s.axes_manager[-1].is_binned = binned
    m = s.create_model()

    m.extend([Gaussian(), Gaussian(), Gaussian()])

    def set_gaussian(gaussian, centre, sigma):
        gaussian.centre.value = centre
        gaussian.centre.free = False
        gaussian.sigma.value = sigma
        gaussian.sigma.free = False

    for gaussian, centre, sigma in zip(m, centre_value_gaussian, sigma_value_gaussian):
        set_gaussian(gaussian, centre, sigma)

    m.fit()
    m.plot(plot_components=plot_component)

    def A_value(s, component, binned):
        if binned:
            return component.A.value * scale
        else:
            return component.A.value

    np.testing.assert_almost_equal(A_value(s, m[0], binned), 100.0, decimal=5)
    np.testing.assert_almost_equal(A_value(s, m[1], binned), 60.0, decimal=5)
    np.testing.assert_almost_equal(A_value(s, m[2], binned), 200.0, decimal=5)

    return m._plot.signal_plot.figure


def test_plot_component():
    m = hs.signals.Signal1D(np.arange(100).reshape(2, 50)).create_model()
    m.append(hs.model.components1D.Gaussian(A=250, sigma=5, centre=20))
    m.plot(plot_components=True)
    ax = m.signal._plot.signal_plot.ax
    p = hs.model.components1D.Polynomial(order=1, a0=-10, a1=0)
    m.append(p)
    assert ax.get_ylim() == (-10.1, 49.0)
    m.remove(0)
    p.estimate_parameters(m.signal, 0, 50)
    assert ax.get_ylim() == (-10.1, 49.0)
    m.remove(0)
    assert ax.get_ylim() == (-0.1, 49.0)
    m.append(p)
    m.signal._plot.close()


@pytest.mark.parametrize(("only_free"), [False, True])
@pytest.mark.parametrize(("only_active"), [False, True])
def test_plot_results(only_free, only_active):
    m = hs.signals.Signal1D(np.arange(100).reshape(2, 50)).create_model()
    m.append(hs.model.components1D.Gaussian(A=250, sigma=5, centre=20))
    m.plot_results(only_free=only_free, only_active=only_active)
