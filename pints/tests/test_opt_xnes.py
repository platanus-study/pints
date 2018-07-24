#!/usr/bin/env python
#
# Tests the basic methods of the XNES optimiser.
#
# This file is part of PINTS.
#  Copyright (c) 2017-2018, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the PINTS
#  software package.
#
import pints
import pints.toy
import unittest
import numpy as np

debug = False
method = pints.XNES

# Consistent unit testing in Python 2 and 3
try:
    unittest.TestCase.assertRaisesRegex
except AttributeError:
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


class TestXNES(unittest.TestCase):
    """
    Tests the basic methods of the XNES optimiser.
    """
    def setUp(self):
        """ Called before every test """
        np.random.seed(1)

    def test_unbounded(self):
        """ Runs an optimisation without boundaries. """
        r = pints.toy.TwistedGaussianLogPDF(2, 0.01)
        x = np.array([0, 1.01])
        opt = pints.Optimisation(r, x, method=method)
        opt.set_log_to_screen(debug)
        found_parameters, found_solution = opt.run()
        self.assertTrue(found_solution < 1e-3)

    def test_bounded(self):
        """ Runs an optimisation with boundaries. """
        r = pints.toy.TwistedGaussianLogPDF(2, 0.01)
        x = np.array([0, 1.01])
        b = pints.RectangularBoundaries([-0.01, 0.95], [0.01, 1.05])
        opt = pints.Optimisation(r, x, boundaries=b, method=method)
        opt.set_log_to_screen(debug)
        found_parameters, found_solution = opt.run()
        self.assertTrue(found_solution < 1e-3)

    def test_bounded_and_sigma(self):
        """ Runs an optimisation without boundaries and sigma. """
        r = pints.toy.TwistedGaussianLogPDF(2, 0.01)
        x = np.array([0, 1.01])
        b = pints.RectangularBoundaries([-0.01, 0.95], [0.01, 1.05])
        s = 0.01
        opt = pints.Optimisation(r, x, s, b, method)
        opt.set_log_to_screen(debug)
        found_parameters, found_solution = opt.run()
        self.assertTrue(found_solution < 1e-3)

    def test_hyper_parameter_interface(self):
        """
        Tests the hyper parameter interface for this optimiser.
        """
        r = pints.toy.RosenbrockError(1, 100)
        x = np.array([1.01, 1.01])
        opt = pints.Optimisation(r, x, method=method)
        m = opt.optimiser()
        self.assertEqual(m.n_hyper_parameters(), 1)
        n = m.population_size() + 2
        m.set_hyper_parameters([n])
        self.assertEqual(m.population_size(), n)
        self.assertRaisesRegex(
            ValueError, 'at least 1', m.set_hyper_parameters, [0])

    def test_ask_tell(self):
        """ Tests ask-and-tell related error handling. """
        x0 = np.array([1.1, 1.1])
        opt = method(x0)

        # Stop called when not running
        self.assertFalse(opt.stop())

        # Best position and score called before run
        self.assertEqual(list(opt.xbest()), list(x0))
        self.assertEqual(opt.fbest(), float('inf'))

        # Tell before ask
        self.assertRaisesRegex(
            Exception, 'ask\(\) not called before tell\(\)', opt.tell, 5)

    def test_name(self):
        """ Test the name() method. """
        opt = pints.XNES(np.array([0, 1.01]))
        self.assertIn('xNES', opt.name())


if __name__ == '__main__':
    print('Add -v for more debug output')
    import sys
    if '-v' in sys.argv:
        debug = True
    unittest.main()
