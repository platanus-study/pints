#
# Nested ellipsoidal sampler implementation.
#
# This file is part of PINTS.
#  Copyright (c) 2017-2019, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the PINTS
#  software package.
#
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals
import pints
import numpy as np
import numpy.linalg as la


class NestedEllipsoidSampler(pints.NestedSampler):
    """
    Creates a nested sampler that estimates the marginal likelihood
    and generates samples from the posterior.

    This is the form of nested sampler described in [1], where an ellipsoid is
    drawn around surviving particles (typically with an enlargement factor to
    avoid missing prior mass), and then random samples are drawn from within
    the bounds of the ellipsoid. By sampling in the space of surviving
    particles, the efficiency of this algorithm should be better than simple
    rejection sampling.

    *Extends:* :class:`NestedSampler`

    [1] "A nested sampling algorithm for cosmological model selection",
    Pia Mukherjee, David Parkinson, Andrew R. Liddle, 2008.
    arXiv: arXiv:astro-ph/0508461v2 11 Jan 2006
    """

    def __init__(self, log_likelihood, log_prior):
        super(NestedEllipsoidSampler, self).__init__(log_likelihood, log_prior)

        # Number of nested rejection samples before starting ellipsoidal
        # sampling
        self._rejection_samples = 0
        self.set_rejection_samples()

        # Gaps between updating ellipsoid
        self._ellipsoid_update_gap = 0
        self.set_ellipsoid_update_gap()

        # Enlargement factor for ellipsoid
        self._enlargement_factor = 0
        self.set_enlargement_factor()

    def ellipsoid_update_gap(self):
        """
        Returns the ellipsoid update gap used in the algorithm (see
        :meth:`set_ellipsoid_update_gap()`).
        """
        return self._ellipsoid_update_gap

    def enlargement_factor(self):
        """
        Returns the enlargement factor used in the algorithm (see
        :meth:`set_enlargement_factor()`).
        """
        return self._enlargement_factor

    def rejection_samples(self):
        """
        Returns the number of rejection sample used in the algorithm (see
        :meth:`set_rejection_samples()`).
        """
        return self._rejection_samples


    def ask(self):
        """
        If in initial phase, then uses rejection sampling. Afterwards,
        points are drawn from within an ellipse (needs to be in uniform
        sampling regime)
        """
        i = self._i

        # If reach end of rejection samples, then determine bounding
        # ellipsoid
        if (i + 1) % self._rejection_samples == 0:
            self._A, self._centroid = self._minimum_volume_ellipsoid(
                self._m_active[:, :self._dimension]
            )
        elif i > self._rejection_samples:
            if ((i + 1 - self._rejection_samples)
                    % self._ellipsoid_update_gap == 0):
                self._A, self._centroid = self._minimum_volume_ellipsoid(
                    self._m_active[:, :self._dimension])

        if i < self._rejection_samples:
            # Start off with rejection sampling, while this is still very
            # efficient.
            proposed = self._log_prior.sample()[0]
        else:
            # After a number of samples, switch to ellipsoid sampling.
            proposed = self._reject_ellipsoid_sample(
                self._enlargement_factor, self._A, self._centroid)

        return proposed

    def set_enlargement_factor(self, enlargement_factor=1.5):
        """
        Sets the factor (>1) by which to increase the minimal volume
        ellipsoidal in rejection sampling. A higher value means it is less
        likely that areas of high probability mass will be missed. A low value
        means that rejection sampling is more efficient.
        """
        if enlargement_factor <= 1:
            raise ValueError('Enlargement factor must exceed 1.')
        self._enlargement_factor = enlargement_factor

    def set_rejection_samples(self, rejection_samples=1000):
        """
        Sets the number of rejection samples to take, which will be assigned
        weights and ultimately produce a set of posterior samples.
        """
        if rejection_samples < 0:
            raise ValueError('Must have non-negative rejection samples.')
        self._rejection_samples = rejection_samples

    def set_ellipsoid_update_gap(self, ellipsoid_update_gap=20):
        """
        Sets the frequency with which the minimum volume ellipsoid is
        re-estimated as part of the nested rejection sampling algorithm. A
        higher rate of this parameter means each sample will be more
        efficiently produced, yet the cost of re-computing the ellipsoid means
        it is often desirable to compute this every n iterates.
        """
        ellipsoid_update_gap = int(ellipsoid_update_gap)
        if ellipsoid_update_gap <= 1:
            raise ValueError('Ellipsoid update gap must exceed 1.')
        self._ellipsoid_update_gap = ellipsoid_update_gap

    def n_hyper_parameters(self):
        """
        Returns the number of hyper-parameters for this method (see
        :class:`TunableMethod`).
        """
        return 3

    def set_hyper_parameters(self, x):
        """
        Sets the hyper-parameters for the method with the given vector of
        values (see :class:`TunableMethod`).

        Hyper-parameter vector is:
            ``[active_points_rate, ellipsoid_update_gap, enlargement_factor]``

        Arguments:

        ``x`` an array of length ``n_hyper_parameters`` used to set the
              hyper-parameters
        """

        self.set_active_points_rate(x[0])
        self.set_ellipsoid_update_gap(x[1])
        self.set_enlargement_factor(x[2])

    def _minimum_volume_ellipsoid(self, points, tol=0.001):
        """
        Finds the ellipse equation in "center form":
        ``(x-c).T * A * (x-c) = 1``.
        """
        N, d = points.shape
        Q = np.column_stack((points, np.ones(N))).T
        err = tol + 1
        u = np.ones(N) / N
        while err > tol:
            # assert(u.sum() == 1) # invariant
            X = np.dot(np.dot(Q, np.diag(u)), Q.T)
            M = np.diag(np.dot(np.dot(Q.T, la.inv(X)), Q))
            jdx = np.argmax(M)
            step_size = (M[jdx] - d - 1) / ((d + 1) * (M[jdx] - 1))
            new_u = (1 - step_size) * u
            new_u[jdx] += step_size
            err = la.norm(new_u - u)
            u = new_u
        c = np.dot(u, points)
        A = la.inv(
            + np.dot(np.dot(points.T, np.diag(u)), points)
            - np.multiply.outer(c, c)
        ) / d
        return A, c

    def _reject_ellipsoid_sample(
            self, enlargement_factor, A, centroid):
        """
        Draws from the enlarged bounding ellipsoid
        """
        return self._draw_from_ellipsoid(
            la.inv((1 / enlargement_factor) * A), centroid, 1)[0]

    def _draw_from_ellipsoid(self, covmat, cent, npts):
        """
        Draw `npts` random uniform points from within an ellipsoid with a
        covariance matrix covmat and a centroid cent, as per:
        http://www.astro.gla.ac.uk/~matthew/blog/?p=368
        """
        try:
            ndims = covmat.shape[0]
        except IndexError:  # pragma: no cover
            ndims = 1

        # calculate eigen_values (e) and eigen_vectors (v)
        eigen_values, eigen_vectors = la.eig(covmat)
        idx = (-eigen_values).argsort()[::-1][:ndims]
        e = eigen_values[idx]
        v = eigen_vectors[:, idx]
        e = np.diag(e)

        # generate radii of hyperspheres
        rs = np.random.uniform(0, 1, npts)

        # generate points
        pt = np.random.normal(0, 1, [npts, ndims])

        # get scalings for each point onto the surface of a unit hypersphere
        fac = np.sum(pt**2, axis=1)

        # calculate scaling for each point to be within the unit hypersphere
        # with radii rs
        fac = (rs**(1 / ndims)) / np.sqrt(fac)
        pnts = np.zeros((npts, ndims))

        # scale points to the ellipsoid using the eigen_values and rotate with
        # the eigen_vectors and add centroid
        d = np.sqrt(np.diag(e))
        d.shape = (ndims, 1)

        for i in range(0, npts):
            # scale points to a uniform distribution within unit hypersphere
            pnts[i, :] = fac[i] * pt[i, :]
            pnts[i, :] = np.dot(
                np.multiply(pnts[i, :], np.transpose(d)),
                np.transpose(v)
            ) + cent

        return pnts

    def name(self):
        """ See :meth:`pints.NestedSampler.name()`. """
        return 'Nested Ellipsoidal Rejection Sampler'

