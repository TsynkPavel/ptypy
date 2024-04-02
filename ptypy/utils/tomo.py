# -*- coding: utf-8 -*-
"""
Numerical util functions.

This file is part of the PTYPY package.

    :copyright: Copyright 2014 by the PTYPY team, see AUTHORS.
    :license: see LICENSE for details.
"""
import numpy as np
import scipy.sparse as sparse
import scipy.ndimage as ndimage
import astra

class AstraTomoWrapperViewBased(object):
    """

    """
    def __init___(self, obj, vol, angles):
        self._obj = obj
        self._vol = vol
        self._angles = angles
        self._create_proj_geometry()
        self._create_volume_geometry()
        self._create_proj_array()

    def _create_proj_array(self):
        self._proj_array = np.moveaxis(np.array([v.data for v in self._obj.views.values()]),2,0)
        self._proj_id_real = astra.data3d.link("-sino", self._proj_geom, self._proj_array.real)
        self._proj_id_imag = astra.data3d.link("-sino", self._proj_geom, self._proj_array.imag)

    def _create_proj_geometry(self):
        self._fsh = np.array([v.shape for v in self._obj.views.values()]).max(axis=0)
        self._vec = np.zeros((len(self._obj.views),12))
        for i,(k,v) in enumerate(self._obj.views.items):

            alpha = self._angles[i]
            y = v.dcoord[0]
            x = v.dcoord[1]

            # ray direction
            self._vec[i,0] = np.sin(alpha)
            self._vec[i,1] = -np.cos(alpha)
            self._vec[i,2] = 0

            # center of detector
            self._vec[i,3] = y * np.cos(alpha)
            self._vec[i,4] = x * np.sin(alpha)
            self._vec[i,5] = x 
            
            # vector from detector pixel (0,0) to (0,1)
            self._vec[i,6] = np.cos(alpha)
            self._vec[i,7] = np.sin(alpha)
            self._vec[i,8] = 0
            
            # vector from detector pixel (0,0) to (1,0)
            self._vec[i,9] = 0
            self._vec[i,10] = 0
            self._vec[i,11] = 1

        self._proj_geom = astra.create_proj_geom('parallel3d_vec',  self._fsh[0], self._fsh[1], self._vec)
        return self._proj_geom

    def _create_volume_geometry(self):
        self._vol_geom = astra.create_vol_geom(self._vol.shape[0],self._vol.shape[1],self._vol.shape[2])
        self._vol_id_real = astra.data3d.link("-vol", self._vol_geom, self._vol.real)
        self._vol_id_imag = astra.data3d.link("-vol", self._vol_geom, self._vol.imag)
        return self._vol_geom, self._vol_id

    def forward(self):
           
        cfg = astra.astra_dict("FP3D_CUDA")
        cfg["VolumeId"] = self._vol_id_real
        cfg["ProjectionDataId"] = self._proj_id_real
        alg_id_real = astra.algorithm.create(cfg)

        cfg = astra.astra_dict("FP3D_CUDA")
        cfg["VolumeId"] = self._vol_id_imag
        cfg["ProjectionDataId"] = self._proj_id_imag
        alg_id_imag = astra.algorithm.create(cfg)

        astra.algorithm.run(alg_id_real)
        astra.algorithm.run(alg_id_imag)

        _proj_data_real = astra.data3d.get(self._proj_id_real)
        _proj_data_imag = astra.data3d.get(self._proj_id_imag)

        _ob_views_real = np.moveaxis(_proj_data_real, 0, 2)
        _ob_views_imag = np.moveaxis(_proj_data_imag, 0, 2)
        for i, (k,v) in enumerate(self._obj.views.items()):
            v.data[:] = _ob_views_real[i] + 1j*_ob_views_imag

    def backward(self, type="BP3D_CUDA", iter=1):
        
        cfg = astra.astra_dict(type)
        cfg["ReconstructionDataId"] = self._vol_id_real
        cfg["ProjectionDataId"] = self._proj_id_real
        alg_id_real = astra.algorithm.create(cfg)

        cfg = astra.astra_dict(type)
        cfg["ReconstructionDataId"] = self._vol_id_imag
        cfg["ProjectionDataId"] = self._proj_id_imag
        alg_id_imag = astra.algorithm.create(cfg)

        astra.algorithm.run(alg_id_real, iter)
        astra.algorithm.run(alg_id_imag, iter)

        vol_real = astra.data3d.get(self._vol_id_real)
        vol_imag = astra.data3d.get(self._vol_id_imag)
        self._vol = vol_real + 1j * vol_imag


def _weights(x, dx=1, orig=0):
    x = np.ravel(x)
    floor_x = np.floor((x - orig) / dx).astype(np.int64)
    alpha = (x - orig - floor_x * dx) / dx
    return np.hstack((floor_x, floor_x + 1)), np.hstack((1 - alpha, alpha))

def _generate_center_coordinates(l_x):
    X, Y = np.mgrid[:l_x, :l_x].astype(np.float64)
    center = l_x / 2.0
    X += 0.5 - center
    Y += 0.5 - center
    return X, Y

## This code is based on this example: https://scikit-learn.org/stable/auto_examples/applications/plot_tomography_l1_reconstruction.html
def forward_projector_matrix_tomo(size, nangles):
    X, Y = _generate_center_coordinates(size)
    angles = np.linspace(0, np.pi, nangles, endpoint=False)
    data_inds, weights, camera_inds = [], [], []
    data_unravel_indices = np.arange(size**2)
    data_unravel_indices = np.hstack((data_unravel_indices, data_unravel_indices))
    for i, angle in enumerate(angles):
        Xrot = np.cos(angle) * X - np.sin(angle) * Y
        inds, w = _weights(Xrot, dx=1, orig=X.min())
        mask = np.logical_and(inds >= 0, inds < size)
        for j in range(size):
            weights += list(w[mask])
            camera_inds += list(inds[mask] + j * size + i * size * size)
            data_inds += list(data_unravel_indices[mask] + j * size * size)
    return sparse.coo_matrix((weights, (camera_inds, data_inds)))

## This code is based on this example: https://scikit-learn.org/stable/auto_examples/applications/plot_tomography_l1_reconstruction.html
def forward_projector_matrix_ptychotomo(vsize, nangles, fsize, pos):
    npos = pos.shape[1]
    X, Y = _generate_center_coordinates(vsize)
    angles = np.linspace(0, np.pi, nangles, endpoint=False)
    data_inds, weights, camera_inds = [], [], []
    data_unravel_indices = np.arange(vsize**2)
    data_unravel_indices = np.hstack((data_unravel_indices, data_unravel_indices))
    for i, angle in enumerate(angles):
        Xrot = np.cos(angle) * X - np.sin(angle) * Y
        inds, w = _weights(Xrot, dx=1, orig=X.min())
        mask = np.logical_and(inds >= 0, inds < vsize)
        for k in range(npos):
            py,px = pos[:,k]
            pmask = np.logical_and(inds >= px, inds < px+fsize)
            for j in range(py, py+fsize):  
                weights += list(w[mask&pmask])
                camera_inds += list(inds[mask&pmask]-px + (j-py) * fsize + k * fsize * fsize + i * npos * fsize * fsize)
                data_inds += list(data_unravel_indices[mask&pmask] + j * vsize * vsize)

    return sparse.coo_matrix((weights, (camera_inds, data_inds)))

def sirt_projectors1(A,b):
    R = sparse.lil_matrix((A.shape[0], A.shape[0]))
    R.setdiag(np.array(1./A.T.sum(axis=0))[0])
    C = sparse.lil_matrix((A.shape[1], A.shape[1]))
    C.setdiag(np.array(1./A.sum(axis=0))[0])
    return C@A.T@R@b, C@A.T@R@A

def sirt_projectors2(A):
    print('Starting sirt_projectors2')
    R = sparse.lil_matrix((A.shape[0], A.shape[0]))
    R.setdiag(np.array(1./A.T.sum(axis=0))[0])
    C = sparse.lil_matrix((A.shape[1], A.shape[1]))
    C.setdiag(np.array(1./A.sum(axis=0))[0])
    print('Finishing sirt_projectors2')
    return C@A.T@R, C@A.T@R@A

def sample_volume(N):
    vol = np.zeros((N,N,N))
    xx,yy,zz = np.meshgrid(np.arange(N)-N/2, np.arange(N)-N/2,np.arange(N)-N/2)
    m = lambda r,dx,dy,dz: np.sqrt((xx+dx)**2 + (yy+dy)**2 + (zz+dz)**2) < r
    vol[m(N//6,0,0,0)] = 1
    vol[m(N//8,N//7,N//7,N//7)] = 2
    vol[m(N//12,N//12,0,0)] = 5
    vol[m(N//12,0,N//6,0)] = 5
    return ndimage.gaussian_filter(vol,1)

def refractive_index_map(Nx):
    beta = np.log(sample_volume(Nx)+20)-np.log(20)
    delta = 0.1 * sample_volume(Nx)
    return delta + 1j * beta