# -*- coding: utf-8 -*-
# Copyright 2007-2022 The HyperSpy developers
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

from functools import wraps

import pytest
import numpy as np

import hyperspy.api as hs

from hyperspy.utils.plot import plot_roi_map


# params different shapes of data, sig, nav dims
@pytest.fixture(
    params=[(1, 1), (1, 2), (2, 1), (2, 2)], ids=lambda sn: f"s{sn[0]}n{sn[1]}"
)
def test_signal(request):
    sig_dims, nav_dims = request.param

    sig_size = 13
    nav_size = 3

    sig_shape = (sig_size,) * sig_dims
    nav_shape = (nav_size,) * nav_dims
    shape = (*nav_shape, *sig_shape)
    test_data = np.zeros(shape)

    axes = []

    for _, name in zip(range(nav_dims), "xyz"):
        axes.append(
            {"name": name, "size": nav_size, "offset": 0, "scale": 1, "units": "um"}
        )

    for _, name in zip(range(sig_dims), ["Ix", "Iy", "Iz"]):
        axes.append(
            {
                "name": name,
                "size": sig_size,
                "offset": 0,
                "scale": 1,
                "units": "nm",
            }
        )
    sig = hs.signals.BaseSignal(
        test_data,
        axes=axes,
    )

    sig = sig.transpose(sig_dims)

    sig.inav[0, ...].isig[0, ...] = 1
    sig.inav[1, ...].isig[2, ...] = 2
    sig.inav[2, ...].isig[4, ...] = 3

    return sig


def sig_mpl_compare(type: set(["sig", "nav"])):
    def wrapper(f):
        @pytest.mark.mpl_image_compare(baseline_dir="plot_roi_map")
        @wraps(f)
        def wrapped(*args, **kwargs):
            sig = f(*args, **kwargs)
            if type == "sig":
                fig = sig._plot.signal_plot.figure
            elif type == "nav":
                fig = sig._plot.navigation_plot.figure

            return fig

        return wrapped

    return wrapper


def test_args_wrong_shape():
    sig2 = hs.signals.BaseSignal(np.empty((1, 1)))

    no_sig = sig2.transpose(0)
    no_nav = sig2.transpose(2)

    sig5 = hs.signals.BaseSignal(np.empty((1, 1, 1, 1, 1)))
    three_sigs = sig5.transpose(3)
    three_navs = sig5.transpose(2)

    unsupported_sigs = [no_sig, no_nav, three_sigs, three_navs]

    for sig in unsupported_sigs:
        with pytest.raises(ValueError):
            plot_roi_map(no_sig, 1)

    for sig in unsupported_sigs:
        # value error also raised because 1D ROI not right shape
        with pytest.raises(ValueError):
            with pytest.warns():
                plot_roi_map(sig, [hs.roi.Point1DROI(0)])


def test_too_many_rois(test_signal):
    plot_roi_map(test_signal, 1)

    with pytest.raises(ValueError):
        plot_roi_map(test_signal, 4)

    with pytest.raises(ValueError):
        plot_roi_map(
            test_signal,
            [
                hs.roi.SpanROI(0, 1),
                hs.roi.SpanROI(1, 2),
                hs.roi.SpanROI(2, 3),
                hs.roi.SpanROI(3, 4),
            ],
        )


def test_passing_rois(test_signal):
    _, int_rois, int_roi_sigs, int_roi_sums = plot_roi_map(test_signal, 3)

    _, rois, roi_sigs, roi_sums = plot_roi_map(test_signal, int_rois)

    assert rois is int_rois

    # passing the rois rather than generating own should yield same results
    assert int_roi_sigs is not roi_sigs
    assert int_roi_sigs == roi_sigs

    assert int_roi_sums is not roi_sums
    assert int_roi_sums == roi_sums


def test_roi_positioning(test_signal):
    _, rois, *_ = plot_roi_map(test_signal, 1)

    sig_size = test_signal.axes_manager.signal_axes[0].size

    assert len(rois) == 1

    assert rois[0].left == pytest.approx(0)
    assert rois[0].right == pytest.approx(sig_size // 2)

    _, rois, *_ = plot_roi_map(test_signal, 2)

    assert len(rois) == 2
    assert rois[0].left == pytest.approx(0)
    assert rois[0].right == pytest.approx(sig_size // 4)
    assert rois[1].left == pytest.approx(sig_size // 4)
    assert rois[1].right == pytest.approx(sig_size // 2)

    # no overlap
    assert rois[0].right <= rois[1].left

    _, rois, *_ = plot_roi_map(test_signal, 3)

    assert len(rois) == 3
    assert rois[0].left == pytest.approx(0)
    assert rois[0].right == pytest.approx(sig_size // 6)
    assert rois[1].left == pytest.approx(sig_size // 6)
    assert rois[1].right == pytest.approx(sig_size // 3)
    assert rois[2].left == pytest.approx(sig_size // 3)
    assert rois[2].right == pytest.approx(sig_size // 2)

    # no overlap
    assert rois[0].right <= rois[1].left and rois[1].right <= rois[2].left


@sig_mpl_compare("sig")
@pytest.mark.parametrize("nrois", [1, 2, 3])
def test_navigator(test_signal, nrois):
    all_sums, rois, roi_sigs, roi_sums = plot_roi_map(test_signal, nrois)

    assert np.all(all_sums.data == test_signal.sum().data)

    return all_sums


@sig_mpl_compare("sig")
@pytest.mark.parametrize("nrois", [1, 2, 3], ids=lambda p: f"rois{p}")
@pytest.mark.parametrize("roi_out", [1, 2, 3], ids=lambda p: f"out{p}")
def test_roi_sums(test_signal, nrois, roi_out):
    all_sums, rois, roi_sigs, roi_sums = plot_roi_map(test_signal, nrois)

    if roi_out > nrois:
        pytest.skip((f"skipping test with roi_out={roi_out} as only " f"nrois={nrois}"))

    roi_sig = roi_sigs[roi_out - 1]
    roi_sum = roi_sums[roi_out - 1]
    roi = rois[roi_out - 1]

    assert np.all(
        np.isclose(roi_sig.nansum(roi_sig.axes_manager.signal_axes).data, roi_sum.data)
    )

    for i in range(3):
        lo, hi = roi.left, roi.right
        within_roi = lo <= (i * 2) < hi

        if within_roi:
            assert np.isin(i + 1, roi_sig.inav[i])
            assert roi_sum.isig[i].data.mean() > 0.0
        else:
            assert not np.isin(i + 1, roi_sig.inav[i])
            assert not (roi_sum.isig[i].data.mean() > 0.0)

    return roi_sum


@sig_mpl_compare("sig")
@pytest.mark.parametrize("which_plot", ["all_sums", "roi_sums"])
def test_interaction(test_signal, which_plot):
    all_sums, rois, roi_sigs, roi_sums = plot_roi_map(test_signal, 1)

    roi_sig = roi_sigs[0]
    roi = rois[0]

    before_move = roi_sig.deepcopy()

    for i in range(3):
        assert np.isin(i + 1, roi_sig.data)

    roi.left = 6.0
    roi.right = 12.0
    roi.left = 6.0
    roi.right = 12.0

    assert before_move.data.shape != roi_sig.data.shape or before_move != roi_sig

    for i in range(3):
        assert not np.isin(i + 1, roi_sig.data)

    if which_plot == "all_sums":
        return all_sums
    elif which_plot == "roi_sums":
        return roi_sums[0]
