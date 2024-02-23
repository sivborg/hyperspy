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

from unittest import mock

import numpy as np
import pytest
from scipy.signal import savgol_filter
import dask.array as da

import hyperspy.api as hs
from hyperspy.decorators import lazifyTestClass
from hyperspy.misc.tv_denoise import _tv_denoise_1d
from hyperspy.signal import BaseSignal


@lazifyTestClass
class TestAlignTools:
    def setup_method(self, method):
        s = hs.signals.Signal1D(np.zeros((10, 100)))
        self.scale = 0.1
        self.offset = -2
        eaxis = s.axes_manager.signal_axes[0]
        eaxis.scale = self.scale
        eaxis.offset = self.offset
        self.izlp = eaxis.value2index(0)
        self.bg = 2
        self.ishifts = np.array([0, 4, 2, -2, 5, -2, -5, -9, -9, -8])
        self.new_offset = self.offset - self.ishifts.min() * self.scale
        s.data[np.arange(10), self.ishifts + self.izlp] = 10
        s.data += self.bg
        self.signal = s

    def test_estimate_shift(self):
        s = self.signal
        eshifts = -1 * s.estimate_shift1D()
        np.testing.assert_allclose(eshifts, self.ishifts * self.scale, atol=1e-3)

    def test_shift1D(self):
        s = self.signal
        m = mock.Mock()
        s.events.data_changed.connect(m.data_changed)
        s.shift1D(-1 * self.ishifts[:, np.newaxis] * self.scale)
        assert m.data_changed.called
        i_zlp = s.axes_manager.signal_axes[0].value2index(0)
        np.testing.assert_allclose(s.data[:, i_zlp], 12)
        # Check that at the edges of the spectrum the value == to the
        # background value. If it wasn't it'll mean that the cropping
        # code is buggy
        np.testing.assert_allclose(s.data[:, -1], 2)
        np.testing.assert_allclose(s.data[:, 0], 2)
        # Check that the calibration is correct
        assert s.axes_manager._axes[1].offset == self.new_offset
        assert s.axes_manager._axes[1].scale == self.scale

    def test_align(self):
        s = self.signal
        s.align1D()
        i_zlp = s.axes_manager.signal_axes[0].value2index(0)
        np.testing.assert_allclose(s.data[:, i_zlp], 12)
        # Check that at the edges of the spectrum the value == to the
        # background value. If it wasn't it'll mean that the cropping
        # code is buggy
        np.testing.assert_allclose(s.data[:, -1], 2)
        np.testing.assert_allclose(s.data[:, 0], 2)
        # Check that the calibration is correct
        assert s.axes_manager._axes[1].offset == self.new_offset
        assert s.axes_manager._axes[1].scale == self.scale

    def test_align_expand(self):
        s = self.signal
        s.align1D(expand=True)
        # Check the numbers of NaNs to make sure expansion happened properly
        Nnan = self.ishifts.max() - self.ishifts.min()
        Nnan_data = np.sum(np.isnan(s.data), axis=1)
        # Due to interpolation, the number of NaNs in the data might
        # be 2 higher (left and right side) than expected
        assert np.all(Nnan_data - Nnan <= 2)

        # Check actual alignment of zlp
        i_zlp = s.axes_manager.signal_axes[0].value2index(0)
        np.testing.assert_allclose(s.data[:, i_zlp], 12)


def test_align1D():
    scale = 0.1
    g = hs.model.components1D.Gaussian(sigma=scale * 5)
    x = np.stack([np.linspace(-5, 5, 100)] * 5)
    s = hs.signals.Signal1D(g.function(x) + 1e5)
    s.axes_manager[-1].scale = scale
    rng = np.random.default_rng(1)
    shifts = rng.random(size=len(s.axes_manager[0].axis)) * 2
    shifts[0] = 0
    s.shift1D(-shifts, show_progressbar=False)
    s.axes_manager.indices = (0,)
    shifts2 = s.estimate_shift1D(show_progressbar=False)
    np.testing.assert_allclose(shifts, shifts2, rtol=0.5)


@lazifyTestClass
class TestShift1D:
    def setup_method(self, method):
        self.s = hs.signals.Signal1D(np.arange(10))
        self.s.axes_manager[0].scale = 0.2

    def test_crop_left(self):
        s = self.s
        shifts = BaseSignal([0.1])
        s.shift1D(shifts, crop=True)
        np.testing.assert_allclose(s.axes_manager[0].axis, np.arange(0.2, 2.0, 0.2))

    def test_crop_right(self):
        s = self.s
        shifts = BaseSignal([-0.1])
        s.shift1D(shifts, crop=True)
        np.testing.assert_allclose(s.axes_manager[0].axis, np.arange(0.0, 1.8, 0.2))

    def test_2D_nav_shift1D(self):
        sig = np.empty((3, 4, 10))
        sig[...] = np.arange(10)
        s = hs.signals.Signal1D(sig)
        s.axes_manager[0].scale = 0.2
        s.axes_manager[1].scale = 0.2
        shifts = np.ones((3, 4)) * 0.1
        s.shift1D(shifts, crop=True)
        np.testing.assert_allclose(s.data[0, 0, :], np.arange(0.9, 9))


@lazifyTestClass
class TestFindPeaks1D:
    def setup_method(self, method):
        x = np.arange(0, 50, 0.01)
        s = hs.signals.Signal1D(np.vstack((np.cos(x), np.sin(x))))
        s.axes_manager.signal_axes[0].scale = 0.01
        self.peak_positions0 = np.arange(8) * 2 * np.pi
        self.peak_positions1 = np.arange(8) * 2 * np.pi + np.pi / 2
        self.signal = s

    def test_single_spectrum(self):
        peaks = self.signal.inav[0].find_peaks1D_ohaver()[0]
        if isinstance(peaks, da.Array):
            peaks = peaks.compute()
        np.testing.assert_allclose(
            peaks["position"], self.peak_positions0, rtol=1e-5, atol=1e-4
        )

    def test_two_spectra(self):
        peaks = self.signal.find_peaks1D_ohaver()[1]
        if isinstance(peaks, da.Array):
            peaks = peaks.compute()
        np.testing.assert_allclose(
            peaks["position"], self.peak_positions1, rtol=1e-5, atol=1e-4
        )

    def test_height(self):
        peaks = self.signal.find_peaks1D_ohaver()[1]
        if isinstance(peaks, da.Array):
            peaks = peaks.compute()
        np.testing.assert_allclose(peaks["height"], 1.0, rtol=1e-5, atol=1e-4)

    def test_width(self):
        peaks = self.signal.find_peaks1D_ohaver()[1]
        if isinstance(peaks, da.Array):
            peaks = peaks.compute()
        np.testing.assert_allclose(peaks["width"], 3.5758, rtol=1e-4, atol=1e-4)

    def test_n_peaks(self):
        peaks = self.signal.find_peaks1D_ohaver()[1]
        if isinstance(peaks, da.Array):
            peaks = peaks.compute()
        assert len(peaks) == 8

    def test_maxpeaksn(self):
        for n in range(1, 10):
            peaks = self.signal.find_peaks1D_ohaver(maxpeakn=n)[1]
            if isinstance(peaks, da.Array):
                peaks = peaks.compute()
            assert len(peaks) == min((8, n))


@lazifyTestClass
class TestInterpolateInBetween:
    def setup_method(self, method):
        s = hs.signals.Signal1D(np.arange(40).reshape((2, 20)))
        s.axes_manager.signal_axes[0].scale = 0.1
        s.isig[8:12] = 0
        self.s = s

    @pytest.mark.parametrize("uniform", [True, False])
    def test_single_spectrum(self, uniform):
        s = self.s.inav[0]
        m = mock.Mock()
        s.events.data_changed.connect(m.data_changed)
        if not uniform:
            s.axes_manager[-1].convert_to_non_uniform_axis()
        s.interpolate_in_between(8, 12)
        np.testing.assert_array_equal(s.data, np.arange(20))
        assert m.data_changed.called

    @pytest.mark.parametrize("uniform", [True, False])
    def test_single_spectrum_in_units(self, uniform):
        s = self.s.inav[0]
        if not uniform:
            s.axes_manager[-1].convert_to_non_uniform_axis()
        s.interpolate_in_between(0.8, 1.2)
        np.testing.assert_array_equal(s.data, np.arange(20))

    def test_two_spectra(self):
        s = self.s
        s.interpolate_in_between(8, 12)
        np.testing.assert_array_equal(s.data, np.arange(40).reshape(2, 20))

    def test_delta_int(self):
        s = self.s.inav[0]
        s.change_dtype("float")
        tmp = np.zeros(s.data.shape)
        tmp[12] = s.data[12]
        s.data += tmp * 9.0
        s.interpolate_in_between(8, 12, delta=2, kind="cubic")
        print(s.data[8:12])
        np.testing.assert_allclose(s.data[8:12], np.array([44.0, 95.4, 139.6, 155.0]))

    @pytest.mark.parametrize("uniform", [True, False])
    def test_delta_float(self, uniform):
        s = self.s.inav[0]
        s.change_dtype("float")
        tmp = np.zeros(s.data.shape)
        tmp[12] = s.data[12]
        s.data += tmp * 9.0
        if not uniform:
            s.axes_manager[0].convert_to_non_uniform_axis()
        s.interpolate_in_between(8, 12, delta=0.31, kind="cubic")
        print(s.data[8:12])
        np.testing.assert_allclose(
            s.data[8:12],
            np.array([46.595205, 109.802805, 164.512803, 178.615201]),
            atol=1,
        )


@lazifyTestClass
class TestEstimatePeakWidth:
    def setup_method(self, method):
        scale = 0.1
        window = 2
        x = np.arange(-window, window, scale)
        g = hs.model.components1D.Gaussian(sigma=0.3)
        s = hs.signals.Signal1D(g.function(x))
        s.axes_manager[-1].scale = scale
        self.s = s
        self.rtol = 1e-7
        self.atol = 0

    def test_full_range(self):
        width, left, right = self.s.estimate_peak_width(
            window=None, return_interval=True
        )
        np.testing.assert_allclose(
            width.data, 0.7065102, rtol=self.rtol, atol=self.atol
        )
        np.testing.assert_allclose(left.data, 1.6467449, rtol=self.rtol, atol=self.atol)
        np.testing.assert_allclose(right.data, 2.353255, rtol=self.rtol, atol=self.atol)
        for t in (width, left, right):
            assert t.metadata.Signal.signal_type == ""
            assert t.axes_manager.signal_dimension == 0

    def test_too_narrow_range(self):
        width, left, right = self.s.estimate_peak_width(
            window=0.5, return_interval=True
        )
        assert np.isnan(width.data).all()
        assert np.isnan(left.data).all()
        assert np.isnan(right.data).all()

    def test_warnings_on_windows(self, caplog):
        import os

        if os.name not in ["nt", "dos"]:
            pytest.skip("Ignored on non-Windows OS")

    def test_two_peaks(self):
        if self.s._lazy:
            pytest.skip("Lazy Signals don't work properly with 0 dimension data")
        s = self.s.deepcopy()
        shifts = BaseSignal([1.0])
        s.shift1D(shifts)
        self.s = self.s.isig[10:] + s
        width, left, right = self.s.estimate_peak_width(
            window=None, return_interval=True
        )
        assert np.isnan(width.data).all()
        assert np.isnan(left.data).all()
        assert np.isnan(right.data).all()


@lazifyTestClass(rtol=1e-4, atol=0.4)
class TestSmoothing:
    def setup_method(self, method):
        n, m = 2, 100
        self.s = hs.signals.Signal1D(np.arange(n * m, dtype="float").reshape(n, m))
        self.s.add_gaussian_noise(0.1, random_state=1)
        self.rtol = 1e-7
        self.atol = 0

    @pytest.mark.parametrize("dtype", ["<f4", "f4", ">f4"])
    def test_lowess(self, dtype):
        from hyperspy.misc.lowess_smooth import lowess

        f = 0.5
        n_iter = 1
        self.rtol = 1e-5
        data = np.asanyarray(self.s.data, dtype=dtype)
        for i in range(data.shape[0]):
            data[i, :] = lowess(
                x=self.s.axes_manager[-1].axis,
                y=data[i, :],
                f=f,
                n_iter=n_iter,
            )
        self.s.smooth_lowess(
            smoothing_parameter=f,
            number_of_iterations=n_iter,
        )
        np.testing.assert_allclose(self.s.data, data, rtol=self.rtol, atol=self.atol)

    def test_tv(self):
        weight = 1
        data = np.asanyarray(self.s.data, dtype="float")
        for i in range(data.shape[0]):
            data[i, :] = _tv_denoise_1d(
                im=data[i, :],
                weight=weight,
            )
        self.s.smooth_tv(
            smoothing_parameter=weight,
        )
        np.testing.assert_allclose(data, self.s.data, rtol=self.rtol, atol=self.atol)

    def test_savgol(self):
        window_length = 13
        polyorder = 1
        deriv = 1
        data = savgol_filter(
            x=self.s.data,
            window_length=window_length,
            polyorder=polyorder,
            deriv=deriv,
            delta=self.s.axes_manager[-1].scale,
            axis=-1,
        )
        self.s.smooth_savitzky_golay(
            window_length=window_length,
            polynomial_order=polyorder,
            differential_order=deriv,
        )
        np.testing.assert_allclose(data, self.s.data)


@pytest.mark.parametrize("lazy", [True, False])
@pytest.mark.parametrize("offset", [3, 0])
def test_hanning(lazy, offset):
    rng = np.random.default_rng(1)
    sig = hs.signals.Signal1D(rng.random(size=(5, 20)))
    if lazy:
        sig = sig.as_lazy()
    data = np.array(sig.data)
    channels = 5
    hanning = np.hanning(channels * 2)
    data[..., :offset] = 0
    data[..., offset : offset + channels] *= hanning[:channels]
    rl = None if offset == 0 else -offset
    data[..., -offset - channels : rl] *= hanning[-channels:]
    if offset != 0:
        data[..., -offset:] = 0

    assert channels == sig.hanning_taper(side="both", channels=channels, offset=offset)
    np.testing.assert_allclose(data, sig.data)


@pytest.mark.parametrize("float_data", [True, False])
def test_hanning_wrong_type(float_data):
    sig = hs.signals.Signal1D(np.arange(100).reshape(5, 20))
    if float_data:
        sig.change_dtype("float")

    if float_data:
        sig.hanning_taper()
    else:
        with pytest.raises(TypeError):
            sig.hanning_taper()
