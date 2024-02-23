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
import logging

from hyperspy._components.expression import Expression
from hyperspy.misc.utils import ordinal


_logger = logging.getLogger(__name__)


class Polynomial(Expression):

    """n-order polynomial component.

    Polynomial component consisting of order + 1 parameters.
    The parameters are named "a" followed by the corresponding order,
    i.e.

    .. math::

        f(x) = a_{2} x^{2} + a_{1} x^{1} + a_{0}

    Zero padding is used for polynomial of order > 10.

    Parameters
    ----------
    order : int
        Order of the polynomial, must be different from 0.
    **kwargs
        Keyword arguments can be used to initialise the value of the
        parameters, i.e. a2=2, a1=3, a0=1. Extra keyword arguments are passed
        to the :class:`~.api.model.components1D.Expression` component.

    """

    def __init__(self, order=2, module=None, **kwargs):
        if order == 0:
            raise ValueError("Polynomial of order 0 is not supported.")
        coeff_list = [
            "{}".format(o).zfill(len(list(str(order)))) for o in range(order, -1, -1)
        ]
        expr = "+".join(
            ["a{}*x**{}".format(c, o) for c, o in zip(coeff_list, range(order, -1, -1))]
        )
        name = "{} order Polynomial".format(ordinal(order))
        super().__init__(
            expression=expr, name=name, module=module, autodoc=False, **kwargs
        )

    def get_polynomial_order(self):
        return len(self.parameters) - 1

    def estimate_parameters(self, signal, x1, x2, only_current=False):
        """Estimate the parameters by the two area method

        Parameters
        ----------
        signal : :class:`~.api.signals.Signal1D`
        x1 : float
            Defines the left limit of the spectral range to use for the
            estimation.
        x2 : float
            Defines the right limit of the spectral range to use for the
            estimation.

        only_current : bool
            If False estimates the parameters for the full dataset.

        Returns
        -------
        bool

        """
        super()._estimate_parameters(signal)
        axis = signal.axes_manager.signal_axes[0]
        i1, i2 = axis.value_range_to_indices(x1, x2)

        if axis.is_binned:
            # using the mean of the gradient for non-uniform axes is a best
            # guess to the scaling of binned signals for the estimation
            scaling_factor = (
                axis.scale
                if axis.is_uniform
                else np.mean(np.gradient(axis.axis), axis=-1)
            )

        if only_current is True:
            estimation = np.polyfit(
                axis.axis[i1:i2],
                signal._get_current_data()[i1:i2],
                self.get_polynomial_order(),
            )
            if axis.is_binned:
                for para, estim in zip(self.parameters[::-1], estimation):
                    para.value = estim / scaling_factor
            else:
                for para, estim in zip(self.parameters[::-1], estimation):
                    para.value = estim
            return True
        else:
            if self.parameters[0].map is None:
                self._create_arrays()

            nav_shape = signal.axes_manager._navigation_shape_in_array
            with signal.unfolded():
                data = signal.data
                # For polyfit the spectrum goes in the first axis
                if axis.index_in_array > 0:
                    data = data.T  # Unfolded, so simply transpose
                fit = np.polyfit(
                    axis.axis[i1:i2], data[i1:i2, ...], self.get_polynomial_order()
                )
                if axis.index_in_array > 0:
                    fit = fit.T  # Transpose back if needed
                # Shape needed to fit parameter.map:
                cmap_shape = nav_shape + (self.get_polynomial_order() + 1,)
                fit = fit.reshape(cmap_shape)

                if axis.is_binned:
                    for i, para in enumerate(self.parameters[::-1]):
                        para.map["values"][:] = fit[..., i] / scaling_factor
                        para.map["is_set"][:] = True
                else:
                    for i, para in enumerate(self.parameters[::-1]):
                        para.map["values"][:] = fit[..., i]
                        para.map["is_set"][:] = True
            self.fetch_stored_values()
            return True


def convert_to_polynomial(poly_dict):
    """
    Convert the dictionary from the old to the new polynomial definition
    """
    _logger.info("Converting the polynomial to the new definition.")
    coeff_list = [
        "{}".format(o).zfill(len(list(str(poly_dict["order"]))))
        for o in range(poly_dict["order"], -1, -1)
    ]
    poly2_dict = dict(poly_dict)
    coefficient_dict = poly_dict["parameters"][0]
    poly2_dict["parameters"] = []
    for i, coeff in enumerate(coeff_list):
        param_dict = dict(coefficient_dict)
        param_dict["_id_name"] = "a{}".format(coeff)
        for v in ["value", "_bounds"]:
            param_dict[v] = coefficient_dict[v][i]
        poly2_dict["parameters"].append(param_dict)

    return poly2_dict
