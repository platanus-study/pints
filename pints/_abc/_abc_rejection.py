#
# ABC Rejection method
#
# This file is part of PINTS.
#  Copyright (c) 2017-2019, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the PINTS
#  software package.
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals
import pints
import numpy as np


class ABCRejection(pints.ABCSampler):
    """
    ABC Rejection.

    Sampling parameters from a user-defined prior distribution, simulating data
    according to a user-defined model comparing against a user-defined
    threshold, and accepting or rejecting.

    [1] ***Citations Needed***
    """
    def __init__(self, log_prior, threshold):

        # Set log_prior
        self._log_prior = log_prior

        # Set threshold
        self._threshold = threshold

        # Initialize param_vals
        self._xs = None

    def name(self):
        """ See :meth:`pints.ABCSampler.name()`. """
        return 'Rejection ABC'

    def ask(self, n_samples):
        """ See :meth:`ABCSampler.ask()`. """
        self._xs = self._log_prior.sample(n_samples)
        return self._xs

    def tell(self, fx):
        """ See :meth:`ABCSampler.tell()`. """
        if isinstance(fx, list):
            accepted = [a < self._threshold for a in fx]
            if np.sum(accepted) == 0:
                return None
            else:
                return [self._xs[c] for c, x in enumerate(accepted) if x]
        else:
            if fx < self._threshold:
                return self._xs
            else:
                return None

    def threshold(self):
        """
        Returns threshold error distance that determines if a sample is
        accepted (is error < threshold).
        """
        return self._threshold

    def set_threshold(self, threshold):
        """
        Sets threshold error distance that determines if a sample is accepted]
        (if error < threshold).
        """
        x = float(threshold)
        if x <= 0:
            raise ValueError('Threshold must be positive.')
        self._threshold = threshold
