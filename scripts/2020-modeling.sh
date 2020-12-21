#!/bin/bash -l
#SBATCH --time=4:00:00
#SBATCH --ntasks-per-node=1
#SBATCH --ncputs-per-task=24
#SBATCH --mem=2gb
#SBATCH --mail-type=ALL
#SBATCH --mail-user=harwe006@umn.edu
#SBATCH --output=R-%x.%j.out
#SBATCH --error=R-%x.%j.err
#SBATCH -J 2020-modeling-0

################################################################################
# Setup Simulation Environment                                                 #
################################################################################
# set -x
export SIERRA_ROOT=$HOME/research/sierra
export FORDYCA_ROOT=$HOME/research/fordyca

# Initialize modules
source /home/gini/shared/swarm/bin/msi-env-setup.sh

# Add ARGoS libraries to system library search path, since they are in a
# non-standard location
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$SWARMROOT/$MSIARCH/lib/argos3

# Set ARGoS library search path. Must contain both the ARGoS core libraries path
# AND the fordyca library path.
export ARGOS_PLUGIN_PATH=$SWARMROOT/$MSIARCH/lib/argos3:$FORDYCA_ROOT/build/lib

# Setup logging (maybe compiled out and unneeded, but maybe not)
export LOG4CXX_CONFIGURATION=$FORDYCA_ROOT/log4cxx.xml

# Set SIERRA ARCH
export SIERRA_ARCH=$MSIARCH

# From MSI docs: transfers all of the loaded modules to the compute nodes (not
# inherited from the master/launch node when using GNU parallel)
export PARALLEL="--workdir . --env PATH --env LD_LIBRARY_PATH --env
LOADEDMODULES --env _LMFILES_ --env MODULE_VERSION --env MODULEPATH --env
MODULEVERSION_STACK --env MODULESHOME --env OMP_DYNAMICS --env
OMP_MAX_ACTIVE_LEVELS --env OMP_NESTED --env OMP_NUM_THREADS --env
OMP_SCHEDULE --env OMP_STACKSIZE --env OMP_THREAD_LIMIT --env OMP_WAIT_POLICY
--env ARGOS_PLUGIN_PATH --env LOG4CXX_CONFIGURATION --env SIERRA_ARCH"


################################################################################
# Begin Experiments                                                            #
################################################################################
OUTPUT_ROOT=$HOME/exp/2020-modeling
TIME_LONG=time_setup.T100000N1000
TIME_SHORT=time_setup.T5000
DENSITY=1p0
CARDINALITY=C8

TASK="$1"

if [ -n "$MSIARCH" ]; then # Running on MSI
    NSIMS=96
    SCENARIOS=(SS.16x8 DS.16x8 RN.8x8 PL.8x8)
    BASE_CMD="python3 sierra.py \
                  --sierra-root=$OUTPUT_ROOT\
                  --template-input-file=$SIERRA_ROOT/templates/ideal.argos \
                  --n-sims=$NSIMS\
                  --controller=d0.CRW\
                  --project=fordyca\
                  --hpc-env=slurm \
                  --no-verify-results\
                  --gen-stddev\
                  --exp-overwrite\
                  --time-setup=${TIME_LONG}"
else
    NSIMS=48
    # SCENARIOS=(SS.16x8 DS.16x8 RN.8x8 PL.8x8)
    SCENARIOS=(RN.8x8)
    BASE_CMD="python3 sierra.py \
                  --sierra-root=$OUTPUT_ROOT\
                  --template-input-file=$SIERRA_ROOT/templates/ideal.argos \
                  --n-sims=$NSIMS\
                  --controller=d0.CRW\
                  --physics-n-engines=2\
                  --project=fordyca --exp-range=6:7 --exec-resume\
                  --hpc-env=local --log-level=DEBUG\
                  --gen-stddev\
                  --no-verify-results\
                  --exp-overwrite\
                  --time-setup=${TIME_SHORT}"


fi

cd $SIERRA_ROOT

if [ "$TASK" == "exp" ] || [ "$TASK" == "all" ]; then

   for s in "${SCENARIOS[@]}"
   do
       # $BASE_CMD --scenario=$s \
       #           --pipeline 1 2 3 4\
       #           --batch-criteria population_density.CD$1p0.I32.${CARDINALITY}

       # $BASE_CMD --scenario=$s \
       #           --pipeline 1 2 3 4\
       #           --batch-criteria population_density.CD2p0.I32.${CARDINALITY}

       # $BASE_CMD --scenario=$s \
       #           --pipeline 1 2 3 4\
       #           --batch-criteria population_density.CD3p0.I32.${CARDINALITY}

       $BASE_CMD --scenario=$s \
                 --pipeline 1 2 3 4\
                 --batch-criteria population_density.CD4p0.I32.${CARDINALITY}

       # $BASE_CMD --scenario=$s \
       #           --pipeline 1 2 3 4\
       #           --batch-criteria population_density.CD5p0.I32.${CARDINALITY}
   done
fi

if [ "$TASK" == "comp" ] || [ "$TASK" == "all" ]; then
    criteria=population_density.CD1p0.I32.${CARDINALITY}

    $BASE_CMD --scenario=$s \
              --pipeline 5\
              --batch-criteria $criteria\
              --bc-univar\
              --scenario-comparison\
              --scenarios-list=SS.16x8,DS.16x8\
              --scenarios-legend="SS","DS"

    $BASE_CMD --scenario=$s \
              --pipeline 5\
              --batch-criteria $criteria\
              --bc-univar\
              --scenario-comparison\
              --scenarios-list=RN.8x8,PL.8x8\
              --scenarios-legend="RN","PL"
fi