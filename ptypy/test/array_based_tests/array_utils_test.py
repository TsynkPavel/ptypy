'''
Tests for the array_utils module
'''


import unittest
import numpy as np
from ptypy.array_based import FLOAT_TYPE, COMPLEX_TYPE
from ptypy.array_based import array_utils as au


class ArrayUtilsTest(unittest.TestCase):

    def test_abs2_real_input(self):
        single_dim = 50.0
        npts = single_dim ** 3
        array_to_be_absed = np.arange(npts)
        absed = np.array([ix**2 for ix in array_to_be_absed])
        array_shape = (int(single_dim), int(single_dim), int(single_dim))
        array_to_be_absed.reshape(array_shape)
        absed.reshape(array_shape)
        out = au.abs2(array_to_be_absed)
        np.testing.assert_array_equal(absed, out)
        self.assertEqual(absed.dtype, np.float)


    def test_abs2_complex_input(self):
        single_dim = 50.0
        array_shape = (int(single_dim), int(single_dim), int(single_dim))
        npts = single_dim ** 3
        array_to_be_absed = np.arange(npts) + 1j * np.arange(npts)
        absed = np.array([np.abs(ix**2) for ix in array_to_be_absed])
        absed.reshape(array_shape)
        array_to_be_absed.reshape(array_shape)
        out = au.abs2(array_to_be_absed)
        np.testing.assert_array_equal(absed, out)
        self.assertEqual(absed.dtype, np.float)

    def test_sum_to_buffer(self):

        I = 4
        X = 2
        M = 4
        N = 4

        in1 = np.empty((I, M, N), dtype=FLOAT_TYPE)

        # fill the input array
        for idx in range(I):
            in1[idx] = np.ones((M, N))* (idx + 1.0)

        outshape = (X, M, N)
        expected_out = np.empty(outshape)

        expected_out[0] = np.ones((M, N)) * 4.0
        expected_out[1] = np.ones((M, N)) * 6.0

        in1_addr = np.empty((I, 3))

        in1_addr = np.array([(0, 0, 0),
                            (1, 0, 0),
                            (2, 0, 0),
                            (3, 0, 0)])

        out1_addr = np.empty_like(in1_addr)
        out1_addr = np.array([(0, 0, 0),
                              (1, 0, 0),
                              (0, 0, 0),
                              (1, 0, 0)])

        out = au.sum_to_buffer(in1, outshape, in1_addr, out1_addr, dtype=FLOAT_TYPE)
        np.testing.assert_array_equal(out, expected_out)


    def test_sum_to_buffer_complex(self):

        I = 4
        X = 2
        M = 4
        N = 4

        in1 = np.empty((I, M, N), dtype=COMPLEX_TYPE)

        # fill the input array
        for idx in range(I):
            in1[idx] = np.ones((M, N))* (idx + 1.0) + 1j * np.ones((M, N))* (idx + 1.0)

        outshape = (X, M, N)
        expected_out = np.empty(outshape, dtype=COMPLEX_TYPE)

        expected_out[0] = np.ones((M, N)) * 4.0 + 1j * np.ones((M, N))* 4.0
        expected_out[1] = np.ones((M, N)) * 6.0+ 1j * np.ones((M, N))* 6.0

        in1_addr = np.empty((I, 3))

        in1_addr = np.array([(0, 0, 0),
                            (1, 0, 0),
                            (2, 0, 0),
                            (3, 0, 0)])

        out1_addr = np.empty_like(in1_addr)
        out1_addr = np.array([(0, 0, 0),
                              (1, 0, 0),
                              (0, 0, 0),
                              (1, 0, 0)])

        out = au.sum_to_buffer(in1, outshape, in1_addr, out1_addr, dtype=COMPLEX_TYPE)

        np.testing.assert_array_equal(out, expected_out)

if __name__=='__main__':
    unittest.main()