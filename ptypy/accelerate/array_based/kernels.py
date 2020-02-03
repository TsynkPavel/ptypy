import numpy as np
from collections import OrderedDict
from ptypy.utils.verbose import logger, log

class Adict(object):

    def __init__(self):
        pass


class BaseKernel(object):

    def __init__(self):
        self.verbose = False
        self.npy = Adict()
        self.benchmark = OrderedDict()

    def log(self, x):
        if self.verbose:
            print(x)


class FourierUpdateKernel(BaseKernel):

    def __init__(self, aux, nmodes=1):

        super(FourierUpdateKernel, self).__init__()
        self.denom = 1e-7
        self.nmodes = np.int32(nmodes)
        ash = aux.shape
        self.fshape = (ash[0] // nmodes, ash[1], ash[2])

        # temporary buffer arrays
        self.npy.fdev = None
        self.npy.ferr = None

        self.kernels = [
            'fourier_error',
            'error_reduce',
            'fmag_all_update'
        ]

    def allocate(self):
        """
        Allocate memory according to the number of modes and
        shape of the diffraction stack.
        """
        # temporary buffer arrays
        self.npy.fdev = np.zeros(self.fshape, dtype=np.float32)
        self.npy.ferr = np.zeros(self.fshape, dtype=np.float32)

    def fourier_error(self, b_aux, addr, mag, mask, mask_sum):
        # reference shape (write-to shape)
        sh = self.fshape
        # stopper
        maxz = mag.shape[0]

        # batch buffers
        fdev = self.npy.fdev[:maxz]
        ferr = self.npy.ferr[:maxz]
        aux = b_aux[:maxz * self.nmodes]

        ## Actual math ##

        # build model from complex fourier magnitudes, summing up 
        # all modes incoherently
        tf = aux.reshape(maxz, self.nmodes, sh[1], sh[2])
        af = np.sqrt((np.abs(tf) ** 2).sum(1))

        # calculate difference to real data (g_mag)
        fdev[:] = af - mag

        # Calculate error on fourier magnitudes on a per-pixel basis
        ferr[:] = mask * np.abs(fdev) ** 2 / mask_sum.reshape((maxz, 1, 1))
        return

    def error_reduce(self, addr, err_sum):
        # reference shape (write-to shape)
        sh = self.fshape

        # stopper
        maxz = err_sum.shape[0]

        # batch buffers
        ferr = self.npy.ferr[:maxz]

        ## Actual math ##

        # Reduces the Fourier error along the last 2 dimensions.fd
        #err_sum[:] = ferr.astype(np.double).sum(-1).sum(-1).astype(np.float)
        err_sum[:] = ferr.sum(-1).sum(-1)
        return

    def fmag_all_update(self, b_aux, addr, mag, mask, err_sum, pbound=0.0):

        sh = self.fshape
        nmodes = self.nmodes

        # stopper
        maxz = mag.shape[0]

        # batch buffers
        fdev = self.npy.fdev[:maxz]
        aux = b_aux[:maxz * nmodes]

        # write-to shape
        ish = aux.shape

        ## Actual math ##

        # local values
        fm = np.ones((maxz, sh[1], sh[2]), np.float32)
        renorm = np.ones((maxz,), np.float32)

        ## As opposed to DM we use renorm to differentiate the cases.

        # pbound >= g_err_sum  
        # fm = 1.0 (as renorm = 1, i.e. renorm[~ind])
        # pbound < g_err_sum :
        # fm = (1 - g_mask) + g_mask * (g_mag + fdev * renorm) / (af + 1e-10) 
        # (as renorm in [0,1])
        # pbound == 0.0 
        # fm = (1 - g_mask) + g_mask * g_mag / (af + 1e-10) (as renorm=0)

        ind = err_sum > pbound
        renorm[ind] = np.sqrt(pbound / err_sum[ind])
        renorm = renorm.reshape((renorm.shape[0], 1, 1))

        af = fdev + mag
        fm[:] = (1 - mask) + mask * (mag + fdev * renorm) / (af + self.denom)

        #fm[:] = mag / (af + 1e-6)
        # upcasting
        aux[:] = (aux.reshape(ish[0] // nmodes, nmodes, ish[1], ish[2]) * fm[:, np.newaxis, :, :]).reshape(ish)
        return

class GradientDescentKernel(BaseKernel):

    def __init__(self, aux, nmodes=1, floating_intensities=False):

        super(GradientDescentKernel, self).__init__()
        self.denom = 1e-7
        self.nmodes = np.int32(nmodes)
        ash = aux.shape
        self.bshape = aux.shape
        self.fshape = (ash[0] // nmodes, ash[1], ash[2])
        # temporary buffer arrays
        self.do_float = floating_intensities
        if self.do_float:
            self.npy.LLden  = None
        self.npy.LLerr = None
        self.npy.Imodel = None

        self.npy.float_err1 = None
        self.npy.float_err2 = None

        self.kernels = [
            'fourier_error',
            'error_reduce',
            'fmag_all_update'
        ]

    def allocate(self):
        """
        Allocate memory according to the number of modes and
        shape of the diffraction stack.
        """
        # temporary buffer arrays
        self.npy.LLden = np.zeros(self.fshape, dtype=np.float32)
        self.npy.LLerr = np.zeros(self.fshape, dtype=np.float32)
        self.npy.Imodel = np.zeros(self.fshape, dtype=np.float32)


    def make_model(self, b_aux, addr):

        # reference shape (write-to shape)
        sh = self.fshape

        # batch buffers
        Imodel = self.npy.Imodel
        aux = b_aux

        ## Actual math ## (subset of FUK.fourier_error)
        tf = aux.reshape(sh[0], self.nmodes, sh[1], sh[2])
        Imodel[:] = (np.abs(tf) ** 2).sum(1)

    def make_a012(self, b_f, b_a, b_b, addr, I):

        # reference shape (write-to shape)
        sh = self.fshape

        # stopper
        maxz = I.shape[0]

        A0 = self.npy.Imodel[:maxz]
        A1 = self.npy.LLerr[:maxz]
        A2 = self.npy.LLden[:maxz]

        # batch buffers
        f = b_f[:maxz]
        a = b_a[:maxz]
        b = b_b[:maxz]

        ## Actual math ## (subset of FUK.fourier_error)
        A0.fill(0.)
        tf = np.abs(f).astype(np.float32) ** 2
        A0[:] = tf.reshape(sh[0], self.nmodes, sh[1], sh[2]).sum(1) - I

        A1.fill(0.)
        tf = 2. * np.real(f * a.conj())
        A1[:] = tf.reshape(sh[0], self.nmodes, sh[1], sh[2]).sum(1) - I

        A2.fill(0.)
        tf = 2. * np.real(f * b.conj()) + np.abs(a) ** 2
        A2[:] = tf.reshape(sh[0], self.nmodes, sh[1], sh[2]).sum(1) - I
        return

    def fill_b(self, addr, Brenorm, w, B):

        # stopper
        maxz = w.shape[0]

        A0 = self.npy.Imodel[:maxz]
        A1 = self.npy.LLerr[:maxz]
        A2 = self.npy.LLden[:maxz]

        ## Actual math ##

        # maybe two kernel calls?

        B[0] += np.dot(w.flat, (A0 ** 2).flat) * Brenorm
        B[1] += np.dot(w.flat, (2 * A0 * A1).flat) * Brenorm
        B[2] += np.dot(w.flat, (A1 ** 2 + 2 * A0 * A2).flat) * Brenorm
        return

    def error_reduce(self, addr, err_sum):
        # reference shape (write-to shape)
        sh = self.fshape

        # stopper
        maxz = err_sum.shape[0]

        # batch buffers
        ferr = self.npy.LLerr[:maxz]

        ## Actual math ##

        # Reduces the LL error along the last 2 dimensions.fd
        err_sum[:] = ferr.sum(-1).sum(-1)
        return

    def main(self, b_aux, addr, w, I):
        # reference shape (write-to shape)
        sh = self.fshape
        nmodes = self.nmodes
        # stopper
        maxz = I.shape[0]

        # batch buffers
        err = self.npy.LLerr[:maxz]
        Imodel = self.npy.Imodel[:maxz]
        aux = b_aux[:maxz*nmodes]

        # write-to shape
        ish = aux.shape

        ## math ##
        DI = Imodel - I
        err[:] = w * DI ** 2
        tmp = w * DI
        aux[:] = (aux.reshape(ish[0] // nmodes, nmodes, ish[1], ish[2]) * tmp[:, np.newaxis, :, :]).reshape(ish)
        return


class AuxiliaryWaveKernel(BaseKernel):

    def __init__(self):
        super(AuxiliaryWaveKernel, self).__init__()
        self.kernels = [
            'build_aux',
            'build_exit',
        ]

    def allocate(self):
        pass

    def build_aux(self, b_aux, addr, ob, pr, ex, alpha=1.0):

        sh = addr.shape

        nmodes = sh[1]

        # stopper
        maxz = sh[0]

        # batch buffers
        aux = b_aux[:maxz * nmodes]
        flat_addr = addr.reshape(maxz * nmodes, sh[2], sh[3])
        rows, cols = ex.shape[-2:]

        for ind, (prc, obc, exc, mac, dic) in enumerate(flat_addr):
            tmp = ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols] * \
                  pr[prc[0], :, :] * \
                  (1. + alpha) - \
                  ex[exc[0], exc[1]:exc[1] + rows, exc[2]:exc[2] + cols] * \
                  alpha
            aux[ind, :, :] = tmp
        return

    def build_exit(self, b_aux, addr, ob, pr, ex):

        sh = addr.shape

        nmodes = sh[1]

        # stopper
        maxz = sh[0]

        # batch buffers
        aux = b_aux[:maxz * nmodes]

        flat_addr = addr.reshape(maxz * nmodes, sh[2], sh[3])
        rows, cols = ex.shape[-2:]

        for ind, (prc, obc, exc, mac, dic) in enumerate(flat_addr):
            dex = aux[ind, :, :] - \
                  ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols] * \
                  pr[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols]

            ex[exc[0], exc[1]:exc[1] + rows, exc[2]:exc[2] + cols] += dex
            aux[ind, :, :] = dex
        return

    def build_aux_no_ex(self, b_aux, addr, ob, pr, fac=1.0, add=False):

        sh = addr.shape

        nmodes = sh[1]

        # stopper
        maxz = sh[0]

        # batch buffers
        aux = b_aux[:maxz * nmodes]
        flat_addr = addr.reshape(maxz * nmodes, sh[2], sh[3])
        rows, cols = b_aux.shape[-2:]

        for ind, (prc, obc, exc, mac, dic) in enumerate(flat_addr):
            tmp = ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols] * \
                  pr[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols] * fac
            if add:
                aux[ind, :, :] += tmp
            else:
                aux[ind, :, :] = tmp
        return

class PoUpdateKernel(BaseKernel):

    def __init__(self):

        super(PoUpdateKernel, self).__init__()
        self.kernels = [
            'pr_update',
            'ob_update',
        ]

    def allocate(self):
        pass

    def ob_update(self, addr, ob, obn, pr, ex):

        sh = addr.shape
        flat_addr = addr.reshape(sh[0] * sh[1], sh[2], sh[3])
        rows, cols = ex.shape[-2:]
        for ind, (prc, obc, exc, mac, dic) in enumerate(flat_addr):
            ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols] += \
                pr[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols].conj() * \
                ex[exc[0], exc[1]:exc[1] + rows, exc[2]:exc[2] + cols]
            obn[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols] += \
                (pr[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols].conj() * \
                pr[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols]).real
        return

    def pr_update(self, addr, pr, prn, ob, ex):

        sh = addr.shape
        flat_addr = addr.reshape(sh[0] * sh[1], sh[2], sh[3])
        rows, cols = ex.shape[-2:]
        for ind, (prc, obc, exc, mac, dic) in enumerate(flat_addr):
            pr[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols] += \
                ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols].conj() * \
                ex[exc[0], exc[1]:exc[1] + rows, exc[2]:exc[2] + cols]
            prn[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols] += \
                (ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols].conj() * \
                ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols]).real
        return

    def ob_update_ML(self, addr, ob, pr, ex, fac=2.0):

        sh = addr.shape
        flat_addr = addr.reshape(sh[0] * sh[1], sh[2], sh[3])
        rows, cols = ex.shape[-2:]
        for ind, (prc, obc, exc, mac, dic) in enumerate(flat_addr):
            ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols] += \
                pr[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols].conj() * \
                ex[exc[0], exc[1]:exc[1] + rows, exc[2]:exc[2] + cols] * fac
        return

    def pr_update_ML(self, addr, pr, ob, ex, fac=2.0):

        sh = addr.shape
        flat_addr = addr.reshape(sh[0] * sh[1], sh[2], sh[3])
        rows, cols = ex.shape[-2:]
        for ind, (prc, obc, exc, mac, dic) in enumerate(flat_addr):
            pr[prc[0], prc[1]:prc[1] + rows, prc[2]:prc[2] + cols] += \
                ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols].conj() * \
                ex[exc[0], exc[1]:exc[1] + rows, exc[2]:exc[2] + cols] * fac
        return

class PositionCorrectionKernel(BaseKernel):
    def __init__(self, aux, nmodes):
        super(PositionCorrectionKernel, self).__init__()
        ash = aux.shape
        self.fshape = (ash[0] // nmodes, ash[1], ash[2])
        self.npy.ferr = None
        self.npy.fdev = None
        self.addr = None
        self.nmodes = nmodes
        self.address_mangler = None
        self.kernels = ['build_aux',
                        'fourier_error',
                        'error_reduce',
                        'update_addr']

    def allocate(self):
        self.npy.fdev = np.zeros(self.fshape, dtype=np.float32) # we won't use this again but preallocate for speed
        self.npy.ferr = np.zeros(self.fshape, dtype=np.float32)

    def build_aux(self, b_aux, addr, ob, pr):
        '''
        different to the AWK, no alpha subtraction. It would be the same, but with alpha permanentaly set to 0.
        '''
        sh = addr.shape

        nmodes = sh[1]

        # stopper
        maxz = sh[0]

        # batch buffers
        aux = b_aux[:maxz * nmodes]
        flat_addr = addr.reshape(maxz * nmodes, sh[2], sh[3])
        rows, cols = aux.shape[-2:]

        for ind, (prc, obc, exc, mac, dic) in enumerate(flat_addr):
            dex = ob[obc[0], obc[1]:obc[1] + rows, obc[2]:obc[2] + cols] * pr[prc[0], :, :]
            aux[ind, :, :] = dex

    def fourier_error(self, b_aux, addr, mag, mask, mask_sum):
        '''
        Should be identical to that of the FUK, but we don't need fdev out.
        '''
        # reference shape (write-to shape)
        sh = self.fshape
        # stopper
        maxz = mag.shape[0]

        # batch buffers
        ferr = self.npy.ferr[:maxz]
        fdev = self.npy.fdev[:maxz]
        aux = b_aux[:maxz * self.nmodes]

        ## Actual math ##

        # build model from complex fourier magnitudes, summing up
        # all modes incoherently
        tf = aux.reshape(maxz, self.nmodes, sh[1], sh[2])
        af = np.sqrt((np.abs(tf) ** 2).sum(1))

        # calculate difference to real data (g_mag)
        fdev[:] = af - mag # we won't reuse this so don't need to keep a persistent buffer

        # Calculate error on fourier magnitudes on a per-pixel basis
        ferr[:] = mask * np.abs(fdev) ** 2 / mask_sum.reshape((maxz, 1, 1))
        return

    def error_reduce(self, addr, err_sum):
        '''
        This should the exact same tree reduction as the FUK.
        '''
        # reference shape (write-to shape)
        sh = self.fshape

        # stopper
        maxz = err_sum.shape[0]

        # batch buffers
        ferr = self.npy.ferr[:maxz]

        ## Actual math ##

        # Reduceses the Fourier error along the last 2 dimensions.fd
        #err_sum[:] = ferr.astype(np.double).sum(-1).sum(-1).astype(np.float)
        err_sum[:] = ferr.sum(-1).sum(-1)
        return

    def update_addr_and_error_state(self, addr, error_state, mangled_addr, err_sum):
        '''
        updates the addresses and err state vector corresponding to the smallest error. I think this can be done on the cpu
        '''
        update_indices = err_sum < error_state
        log(4, "updating %s indices" % np.sum(update_indices))
        addr[update_indices] = mangled_addr[update_indices]
        error_state[update_indices] = err_sum[update_indices]
