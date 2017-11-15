from proteus.default_n import *
import ladr_2d_p as p
timeIntegration = BackwardEuler_cfl
stepController = Min_dt_cfl_controller
runCFL=1.0
femSpaces = {0:C0_AffineLinearOnSimplexWithNodalBasis}
elementQuadrature = SimplexGaussQuadrature(p.nd,3)
elementBoundaryQuadrature = SimplexGaussQuadrature(p.nd-1,3)
subgridError = AdvectionDiffusionReaction_ASGS(p.coefficients,p.nd,lag=False)
shockCapturing = ResGradQuad_SC(p.coefficients,p.nd,
                               shockCapturingFactor=0.99,
                               lag=True)
numericalFluxType = Advection_DiagonalUpwind_Diffusion_SIPG_exterior
nnx=41; nny=41
tnList=[float(i)/40.0 for i in range(11)]
matrix = SparseMatrix
multilevelLinearSolver = KSP_petsc4py
linearSmoother = None
l_atol_res = 1.0e-8
parallelPartitioningType = MeshParallelPartitioningTypes.node
nLayersOfOverlapForParallel =0
