from proteus import Domain, Context
from proteus.mprans import SpatialTools as st
from proteus import WaveTools as wt
import numpy as np


# ----- DEFINING CONTEXT OPTIONS AND THEIR DEFAULT VALUE ------ #
opts=Context.Options([
    # predefined test cases
    ("water_level", 0.25, "Height of free surface above bottom"),
    # tank
    ("tank_dim", (3., 0.5), "Dimensions of the tank"),
    ("tank_sponge", (1., 1.), "Length of absorption zones (front/back, left/right)"),
    # waves
    ("waves", False, "Generate waves (True/False)"),
    ("wave_period", 0.8, "Period of the waves"),
    ("wave_height", 0.029, "Height of the waves"),
    ("wave_dir", (1., 0., 0.), "Direction of the waves (from left boundary)"),
    # caisson
    ("caisson_dim", (0.3, 0.1), "Dimensions of the caisson"),
    ("caisson_coords", None, "Coordinates of the caisson"),
    ("caisson_mass", 1., "Mass of the caisson"),
    ("caisson_width", 0.9, "Width of the caisson"),
    ("free_x", (0.0, 0.0, 0.0), "Translational DOFs"),
    ("free_r", (0.0, 0.0, 1.0), "Rotational DOFs"),
    ("VCG", None, "vertical position of the barycenter of the caisson"),
    ("inertia", 0.236, "Inertia of the caisson"),
    ("rotation_angle", np.pi/12., "Initial rotation angle (in radians)"),
    # numerical options
    ("refinement_level", 0 ,"Set maximum element diameter to he/2**refinement_level"),
    ("T", 3.0 ,"Simulation time"),
    ("dt_init", 0.001 ,"Initial time step"),
    ("cfl", 0.9 ,"Target cfl"),
    ("nsave",  1.,"Number of time steps to save per second"),
    ("parallel", True ,"Run in parallel")])


# ----- MANIPULATING CONTEXT OPTIONS ------ #

# general options
waterLevel = opts.water_level

# waves
if opts.waves is True:
    wave = wt.MonochromaticWaves(period=opts.wave_period, waveHeight=opts.wave_height, mwl=opts.water_level, 
                                 depth=opts.water_level, g=np.array([0., -9.81, 0.]), waveDir=opts.wave_dir)
    print('wavelength of monochromatic wave:', wave.wavelength)

# tank options
tank_dim = opts.tank_dim
tank_sponge = opts.tank_sponge

# caisson options
dim = opts.caisson_dim
VCG = opts.VCG
if VCG is None:
    VCG = dim[1]/2.
free_x = opts.free_x
free_r = opts.free_r
rotation = opts.rotation_angle
if opts.caisson_coords is None:
    coords = [tank_dim[0]/2., waterLevel]
else:
    coords = opts.caisson_coords
barycenter = (coords[0], coords[1]-dim[1]/2.+VCG)
inertia = opts.inertia
width = opts.caisson_width


# ----- DOMAIN ----- #
# the Domain class instance that will be used by the model must be called "domain"

domain = Domain.PlanarStraightLineGraphDomain()


# ----- SHAPES ----- #

tank = st.Tank2D(domain, tank_dim)
tank.setSponge(left=tank_sponge[0], right=tank_sponge[1])
left = bool(tank_sponge[0])
right = bool(tank_sponge[1])
if opts.waves is True:
    tank.setGenerationZones(left=left, waves=wave)
else:
    tank.setAbsorptionZones(left=left)
tank.setAbsorptionZones(right=right)

caisson3D = st.Rectangle(domain, dim=dim, coords=coords)
caisson3D.setRigidBody()
caisson3D.setMass(opts.caisson_mass)
caisson3D.setConstraints(free_x=free_x, free_r=free_r)
if rotation:
    caisson3D.rotate(rotation)  # initial position for free oscillation
caisson3D.It = inertia/caisson3D.mass/width
caisson3D.setRecordValues(pos=True, rot=True, F=True, M=True)


# ----- BOUNDARY CONDITIONS ----- #

for bc in caisson3D.BC_list:
    bc.setNoSlip()
    
for bc in tank.BC_list:
    bc.setFixedNodes()
tank.BC_dict['top'].setOpenAir()
tank.BC_dict['bottom'].setNoSlip()
if opts.waves is True:
    tank.BC_dict['left'].setUnsteadyTwoPhaseVelocityInlet(wave, vert_axis=1)
else:
    tank.BC_dict['left'].setNoSlip()
tank.BC_dict['right'].setNoSlip()
tank.BC_dict['sponge'].setNonMaterial()


# ----- MESH OPTIONS ----- #

# mesh options can be used set from the domain.
refinement_level = opts.refinement_level
he = (caisson3D.dim[-1])/5.0*(0.5**refinement_level)
domain.MeshOptions.elementSize(he, refinement_level) #coarse grid


# ----- ASSEMBLING ----- #
# always the last step

st.assembleDomain(domain)




##########################################
# Numerical Options and other parameters #
##########################################
# the values can be modified but the names of these parameters should not be changed
# (might be incorporated in a class in the future for convenience)
from proteus.default_n import *


rho_0=998.2  # water density
nu_0 =1.004e-6  # water viscosity
rho_1=1.205  # air density
nu_1 =1.500e-5  # air viscosity

nd = domain.nd
if nd == 2:
    g = [0., -9.81]
elif nd == 3:
    g = [0., 0., -9.81]


#----------------------------------------------------
movingDomain=True
checkMass=False
applyCorrection=True
applyRedistancing=True
freezeLevelSet=True

#----------------------------------------------------
# Time stepping and velocity
#----------------------------------------------------
weak_bc_penalty_constant = 10.0/nu_0#Re
dt_init = opts.dt_init
T = opts.T
nDTout = int(opts.T*opts.nsave)
dt_out =  (T-dt_init)/nDTout
runCFL = opts.cfl

#----------------------------------------------------

#  Discretization -- input options
useOldPETSc=False
useSuperlu = not True
spaceOrder = 1
useHex     = False
useRBLES   = 0.0
useMetrics = 1.0
useVF = 1.0
useOnlyVF = False
useRANS = 0 # 0 -- None
            # 1 -- K-Epsilon
            # 2 -- K-Omega, 1998
            # 3 -- K-Omega, 1988
# Input checks
if spaceOrder not in [1,2]:
    print "INVALID: spaceOrder" + spaceOrder
    sys.exit()

if useRBLES not in [0.0, 1.0]:
    print "INVALID: useRBLES" + useRBLES
    sys.exit()

if useMetrics not in [0.0, 1.0]:
    print "INVALID: useMetrics"
    sys.exit()

#  Discretization
nd = 2
if spaceOrder == 1:
    hFactor=1.0
    if useHex:
        basis=C0_AffineLinearOnCubeWithNodalBasis
        elementQuadrature = CubeGaussQuadrature(nd,3)
        elementBoundaryQuadrature = CubeGaussQuadrature(nd-1,3)
    else:
        basis=C0_AffineLinearOnSimplexWithNodalBasis
        elementQuadrature = SimplexGaussQuadrature(nd,3)
        elementBoundaryQuadrature = SimplexGaussQuadrature(nd-1,3)
         #elementBoundaryQuadrature = SimplexLobattoQuadrature(nd-1,1)
elif spaceOrder == 2:
    hFactor=0.5
    if useHex:
        basis=C0_AffineLagrangeOnCubeWithNodalBasis
        elementQuadrature = CubeGaussQuadrature(nd,4)
        elementBoundaryQuadrature = CubeGaussQuadrature(nd-1,4)
    else:
        basis=C0_AffineQuadraticOnSimplexWithNodalBasis
        elementQuadrature = SimplexGaussQuadrature(nd,4)
        elementBoundaryQuadrature = SimplexGaussQuadrature(nd-1,4)


# Numerical parameters
ns_forceStrongDirichlet = False
backgroundDiffusionFactor=0.01
if useMetrics:
    ns_shockCapturingFactor  = 0.5
    ns_lag_shockCapturing = True
    ns_lag_subgridError = True
    ls_shockCapturingFactor  = 0.5
    ls_lag_shockCapturing = True
    ls_sc_uref  = 1.0
    ls_sc_beta  = 1.5
    vof_shockCapturingFactor = 0.5
    vof_lag_shockCapturing = True
    vof_sc_uref = 1.0
    vof_sc_beta = 1.5
    rd_shockCapturingFactor  = 0.5
    rd_lag_shockCapturing = False
    epsFact_density    = 3.0
    epsFact_viscosity  = epsFact_curvature  = epsFact_vof = epsFact_consrv_heaviside = epsFact_consrv_dirac = epsFact_density
    epsFact_redistance = 0.33
    epsFact_consrv_diffusion = 1.0
    redist_Newton = True
    kappa_shockCapturingFactor = 0.5
    kappa_lag_shockCapturing = True
    kappa_sc_uref = 1.0
    kappa_sc_beta = 1.5
    dissipation_shockCapturingFactor = 0.5
    dissipation_lag_shockCapturing = True
    dissipation_sc_uref = 1.0
    dissipation_sc_beta = 1.5
else:
    ns_shockCapturingFactor  = 0.9
    ns_lag_shockCapturing = True
    ns_lag_subgridError = True
    ls_shockCapturingFactor  = 0.9
    ls_lag_shockCapturing = True
    ls_sc_uref  = 1.0
    ls_sc_beta  = 1.0
    vof_shockCapturingFactor = 0.9
    vof_lag_shockCapturing = True
    vof_sc_uref  = 1.0
    vof_sc_beta  = 1.0
    rd_shockCapturingFactor  = 0.9
    rd_lag_shockCapturing = False
    epsFact_density    = 1.5
    epsFact_viscosity  = epsFact_curvature  = epsFact_vof = epsFact_consrv_heaviside = epsFact_consrv_dirac = epsFact_density
    epsFact_redistance = 0.33
    epsFact_consrv_diffusion = 10.0
    redist_Newton = False#True
    kappa_shockCapturingFactor = 0.9
    kappa_lag_shockCapturing = True#False
    kappa_sc_uref  = 1.0
    kappa_sc_beta  = 1.0
    dissipation_shockCapturingFactor = 0.9
    dissipation_lag_shockCapturing = True#False
    dissipation_sc_uref  = 1.0
    dissipation_sc_beta  = 1.0

ns_nl_atol_res = max(1.0e-12,0.001*domain.MeshOptions.he**2)
vof_nl_atol_res = max(1.0e-12,0.001*domain.MeshOptions.he**2)
ls_nl_atol_res = max(1.0e-12,0.001*domain.MeshOptions.he**2)
mcorr_nl_atol_res = max(1.0e-12,0.0001*domain.MeshOptions.he**2)
rd_nl_atol_res = max(1.0e-12,0.01*domain.MeshOptions.he)
kappa_nl_atol_res = max(1.0e-12,0.001*domain.MeshOptions.he**2)
dissipation_nl_atol_res = max(1.0e-12,0.001*domain.MeshOptions.he**2)
mesh_nl_atol_res = max(1.0e-12,0.001*domain.MeshOptions.he**2)

#turbulence
ns_closure=0 #1-classic smagorinsky, 2-dynamic smagorinsky, 3 -- k-epsilon, 4 -- k-omega

if useRANS == 1:
    ns_closure = 3
elif useRANS >= 2:
    ns_closure == 4