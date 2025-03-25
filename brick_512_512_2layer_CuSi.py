"""
This script is a test for ptychographic reconstruction in the absence
of actual data. It uses a simulated Au Siemens star pattern under  
experimental farfield conditions in the hard X-ray regime.
"""
from matplotlib import pyplot as plt
from ptypy.core import Ptycho
from ptypy import utils as u
import numpy as np
import tempfile
tmpdir = tempfile.gettempdir()
import datetime
import ptypy
import argparse
import ptypy.utils.plot_client as pc
from pathlib import Path
from math import *

ptypy.load_gpu_engines(arch="cupy")

parser = argparse.ArgumentParser()
parser.add_argument('--steps', dest='steps', type=str, default=10)
parser.add_argument('--spacing', dest='spacing', type=str, default=1e-6)
args = parser.parse_args()

### PTYCHO PARAMETERS
p = u.Param()
p.verbose_level = "info"
p.run = None

p.data_type = "single"
p.run = None
p.io = u.Param()
now = datetime.datetime.now()
st = str(now)
p.io.autosave = u.Param(active=False)

output_dir = Path("results")
if args.steps is not None:
    output_dir = output_dir / f"steps_{args.steps}"
# if args.central_stop is not None:
#     output_dir = output_dir / f"central_stop_{args.central_stop}"
if args.spacing is not None:
    output_dir = output_dir / f"spacing_{args.spacing}"
# if args.focussed is not None:
#     output_dir = output_dir / f"focussed_{args.focussed}"
# if args.photons is not None:
#     output_dir = output_dir / f"photons_{args.photons}"
# if args.spot_size is not None:
#     output_dir = output_dir / f"spot_size_{args.spot_size}"
# if args.parallel is not None:
#     output_dir = output_dir / f"parallel_{args.parallel}"
p.io.home = str(output_dir)
p.io.autoplot =  u.Param()

# Simulation parameters
sim = u.Param()
sim.energy = 8.8
sim.distance = 2
sim.psize = 55e-6
sim.shape = 512

sim.xy = u.Param()
sim.xy.model = 'raster'
sim.xy.steps = int(args.steps)
sim.xy.spacing = float(args.spacing)
sim.xy.extent = None
sim.verbose_level = 0

sim.illumination = u.Param()
sim.illumination.model = None
sim.illumination.photons = 1e11
sim.illumination.aperture = u.Param()
sim.illumination.aperture.diffuser = (8.0, 10.0)
sim.illumination.aperture.form = "circ"
sim.illumination.aperture.size = 5e-6
sim.illumination.aperture.central_stop = None
sim.illumination.propagation = u.Param()
sim.illumination.propagation.focussed = None
sim.illumination.propagation.parallel = 5e-3
sim.illumination.propagation.spot_size = None

points = np.load('ptypy/resources/npr/brick_512_512_2layer_CuSi.npy')

sim.sample = u.Param()

sim.sample.model =points #points[::-1,:]

sim.sample.process = u.Param()
sim.sample.process.offset = (0,0)
sim.sample.process.zoom = None
sim.sample.process.formula = None #"Au"
sim.sample.process.density = None #19.3
sim.sample.process.thickness = None #700e-9
sim.sample.process.ref_index = None
sim.sample.process.smoothing = None
sim.sample.fill = 0+0.j

sim.detector = 'GenericCCD32bit'
sim.detector = u.Param()
sim.detector.dtype = np.uint32
sim.detector.full_well = 2**32-1
sim.detector.psf = 0.0 # Point spread function of the detector
sim.detector.modules = [ 12, 12 ] # 12 x 12 modules of 256x256 pixels
sim.detector.gaps = 3 # pixels in gaps betwen modules
sim.plot = True # Plot overviews

# Scan model and initial value parameters
p.scans = u.Param()
p.scans.scan00 = u.Param()
p.scans.scan00.name = 'BlockFull'

p.scans.scan00.coherence = u.Param()
p.scans.scan00.coherence.num_probe_modes = 1
p.scans.scan00.coherence.num_object_modes = 1
p.scans.scan00.coherence.energies = [1.0]

p.scans.scan00.sample = u.Param()


# (copy simulation illumination and modify some things)
p.scans.scan00.illumination = sim.illumination.copy(99)
p.scans.scan00.illumination.aperture.central_stop = None

# Scan data (simulation) parameters
p.scans.scan00.data=u.Param()
p.scans.scan00.data.name = 'SimScan'
p.scans.scan00.data.propagation = 'farfield'
p.scans.scan00.data.save = None #'append'
p.scans.scan00.data.shape = None
p.scans.scan00.data.num_frames = None
p.scans.scan00.data.update(sim)

# Reconstruction parameters
p.engines = u.Param()
p.engines.engine00 = u.Param()
p.engines.engine00.name = 'DM_cupy'

p.engines.engine00.numiter = 100
p.engines.engine00.fourier_relax_factor = 0.05
p.engines.engine00.numiter_contiguous = 1
p.engines.engine00.probe_support = 0.7
p.engines.engine00.probe_inertia = 0.01
p.engines.engine00.object_inertia = 0.1
p.engines.engine00.clip_object = (0, 1.)
p.engines.engine00.alpha = 1
p.engines.engine00.probe_update_start = 2
p.engines.engine00.update_object_first = True
p.engines.engine00.overlap_converge_factor = 0.05
p.engines.engine00.overlap_max_iterations = 10
p.engines.engine00.obj_smooth_std = 5

if __name__ == "__main__":
    P = Ptycho(p,level=5)

