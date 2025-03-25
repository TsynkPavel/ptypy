"""
This script is a test for ptychographic reconstruction in the absence
of actual data. It uses a simulated Au Siemens star pattern under
experimental farfield conditions in the hard X-ray regime.
"""

from ptypy.core import Ptycho
from ptypy import utils as u
import numpy as np
import ptypy

import tempfile
from pathlib import Path

tmpdir = tempfile.gettempdir()

xmax = 3000
ymax = 3000
zmax = 16
import argparse

parser = argparse.ArgumentParser(description="Rotate Simence star.")
parser.add_argument("--central-stop", dest="central_stop", type=str, default=None)
parser.add_argument("--aperture-size", dest="aperture_size", type=str, default=0.5e-5)
parser.add_argument("--spacing", dest="spacing", type=str, default=250e-9)
parser.add_argument("--focussed", dest="focussed", type=str, default=0.01)
parser.add_argument("--photons", dest="photons", type=str)
parser.add_argument("--spot-size", dest="spot_size", type=str)
parser.add_argument("--parallel", dest="parallel", type=str)

args = parser.parse_args()

### PTYCHO PARAMETERS
p = u.Param()
p.verbose_level = "info"
p.run = None

p.data_type = "single"
p.run = None
p.io = u.Param()

output_dir = Path("results")
if args.aperture_size is not None:
    output_dir = output_dir / f"aperture_size_{args.aperture_size}"
if args.central_stop is not None:
    output_dir = output_dir / f"central_stop_{args.central_stop}"
if args.spacing is not None:
    output_dir = output_dir / f"spacing_{args.spacing}"
if args.focussed is not None:
    output_dir = output_dir / f"focussed_{args.focussed}"
if args.photons is not None:
    output_dir = output_dir / f"photons_{args.photons}"
if args.spot_size is not None:
    output_dir = output_dir / f"spot_size_{args.spot_size}"
if args.parallel is not None:
    output_dir = output_dir / f"parallel_{args.parallel}"

p.io.home = str(output_dir)

p.io.autoplot = u.Param()
p.io.autoplot.layout = "nearfield"

# Simulation parameters
sim = u.Param()
sim.energy = 9.0
sim.distance = 8  # we want 8 m
sim.psize = 100e-6  # we want 100 um
sim.shape = 3072  # we want 3000 x 3000
sim.label = "AuStar-focus"

sim.xy = u.Param()
sim.xy.model = "raster"
sim.xy.steps = 5  # grid 5x5
sim.xy.spacing = float(args.spacing)  #250e-9  # Scaning step
sim.xy.extent = None  # 4e-6  # Scaning aria
sim.verbose_level = 1
"""
Алгоритм такой:
    if steps is None:
        steps = (extent / spacing)
    elif spacing is None:
        spacing = extent / steps
    else:
        extent = steps * spacing
"""

sim.illumination = u.Param()
sim.illumination.model = None
sim.illumination.photons = float(args.photons) # 1e11
sim.illumination.aperture = u.Param()
sim.illumination.aperture.diffuser = (8.0, 10.0)
sim.illumination.aperture.form = "circ"
sim.illumination.aperture.size = float(args.aperture_size)  # 0.5e-5  # we want 1e-3
if args.central_stop is not None:
    sim.illumination.aperture.central_stop = float(args.central_stop)
else:
    sim.illumination.aperture.central_stop = None
sim.illumination.propagation = u.Param()
sim.illumination.propagation.focussed = float(args.focussed)  # we want 10 mm = 0.01
if args.parallel is not None:
    sim.illumination.propagation.parallel = float(args.parallel)  # None is for farfield
else:
    sim.illumination.propagation.parallel = None  # None is for farfield
sim.illumination.propagation.spot_size = float(args.spot_size)

sim.sample = u.Param()
# sim.sample.model = u.xradia_star((1200,1200),minfeature=3,contrast=0.8)

# from utils.object_transform import ptypy_object_rotate


# Star as (x,y) points
print("Create XRadia star")
X3 = u.xradia_star((xmax, ymax), 48, std=0.2, rings=10, minfeature=1, contrast=0.5)
print("The XRadia star is created")

sim.sample.model = X3

sim.sample.process = u.Param()
sim.sample.process.offset = (0, 0)
sim.sample.process.zoom = 1.0
sim.sample.process.formula = "Au"
sim.sample.process.density = 19.3
sim.sample.process.thickness = 700e-9
sim.sample.process.ref_index = None
sim.sample.process.smoothing = None
sim.sample.fill = 1.0 + 0.0j

# sim.detector = 'GenericCCD32bit'
sim.detector = u.Param()
sim.detector.dtype = np.uint32
sim.detector.full_well = 2**32 - 1
sim.detector.psf = 0.0  # Point spread function of the detector
sim.detector.shape = 3072  # 3k x 3k pixels
sim.detector.modules = [12, 12]  # 12 x 12 modules of 256x256 pixels
sim.detector.gaps = 3  # pixels in gaps betwen modules
sim.detector.center = 1536  # the center of the detector
sim.detector.psize = 100e-06  # pixes size in meters

sim.plot = True  # Plot overviews

# Scan model and initial value parameters
p.scans = u.Param()
p.scans.scan00 = u.Param()
p.scans.scan00.name = "BlockFull"

p.scans.scan00.coherence = u.Param()
p.scans.scan00.coherence.num_probe_modes = 1
p.scans.scan00.coherence.num_object_modes = 1
p.scans.scan00.coherence.energies = [1.0]

p.scans.scan00.sample = u.Param()

# (copy simulation illumination and modify some things)
p.scans.scan00.illumination = sim.illumination.copy(99)
# p.scans.scan00.illumination.aperture.size = 10e-6
if args.central_stop is not None:
    sim.illumination.aperture.central_stop = float(args.central_stop)
else:
    sim.illumination.aperture.central_stop = None

# Scan data (simulation) parameters
p.scans.scan00.data = u.Param()
p.scans.scan00.data.name = "SimScan"
p.scans.scan00.data.propagation = "farfield"
p.scans.scan00.data.save = None  #'append'
p.scans.scan00.data.shape = None
p.scans.scan00.data.num_frames = None

p.scans.scan00.data.update(sim)

# Reconstruction parameters
p.engines = u.Param()
p.engines.engine00 = u.Param()
p.engines.engine00.name = "DM"
p.engines.engine00.numiter = 100  # we want 100
p.engines.engine00.object_inertia = 1.0
p.engines.engine00.numiter_contiguous = 1
p.engines.engine00.probe_support = None
p.engines.engine00.probe_inertia = 0.001
p.engines.engine00.obj_smooth_std = 10
p.engines.engine00.clip_object = None
p.engines.engine00.alpha = 1
p.engines.engine00.probe_update_start = 2
p.engines.engine00.update_object_first = True
p.engines.engine00.overlap_converge_factor = 0.5
p.engines.engine00.overlap_max_iterations = 100
p.engines.engine00.fourier_relax_factor = 0.05

# p.engines.engine01 = u.Param()
# p.engines.engine01.name = "ML"
# p.engines.engine01.numiter = 50  # we want 50

if __name__ == "__main__":
    P = Ptycho(p, level=5)
    # input("Press the <Enter> key to continue...")
