#!/bin/bash -l
#SBATCH --time=12:00:00
#SBATCH --nodes 32
#SBATCH --cpus-per-task=24
#SBATCH --mem-per-cpu=2G
#SBATCH --mail-type=ALL
#SBATCH --mail-user=harwe006@umn.edu
#SBATCH --output=R-%x.%j.out
#SBATCH --error=R-%x.%j.err
#SBATCH -J 2021-modeling-0

################################################################################
# Setup Simulation Environment                                                 #
################################################################################
# set -x

# Initialize modules
source /home/gini/shared/swarm/bin/msi-env-setup.sh

if [ -n "$MSIARCH" ]; then # Running on MSI
    export SIERRA_ROOT=$HOME/research/$MSIARCH/sierra
    export FORDYCA_ROOT=$HOME/research/$MSIARCH/fordyca
else
    export SIERRA_ROOT=$HOME/git/sierra
    export FORDYCA_ROOT=$HOME/git/fordyca
fi

# Set ARGoS library search path. Must contain both the ARGoS core libraries path
# AND the fordyca library path.
export ARGOS_PLUGIN_PATH=$ARGOS_PLUGIN_PATH:$FORDYCA_ROOT/build/lib

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
OUTPUT_ROOT=$HOME/exp/test/2021-ijcai-new
TIME_LONG=time_setup.T20000
DENSITY=CD1p0
CARDINALITY=C16
SIZEINC=I16
SCENARIOS_LIST=(SS.16x8x2 DS.16x8x2 RN.8x8x2 PL.8x8x2)
# SCENARIOS_LIST=(SS.16x8 DS.16x8)
SCENARIOS_LIST=(PL.8x8x2)
NSIMS=32

SIERRA_BASE_CMD="python3 sierra.py \
                  --sierra-root=$OUTPUT_ROOT\
                  --template-input-file=$SIERRA_ROOT/templates/2021-ijcai.argos \
                  --n-sims=$NSIMS\
                  --controller=d0.CRW\
                  --project=fordyca\
                  --log-level=INFO\
                  --pipeline 4 --project-no-yaml-LN\
                  --dist-stats=conf95\
                  --with-robot-leds\
                  --log-level=DEBUG\
                  --exp-overwrite\
                  --time-setup=${TIME_LONG}"

if [ -n "$MSIARCH" ]; then # Running on MSI
    # 4 scenarios, each one containing 16 experiments
    EXP_NUM=$(($SLURM_ARRAY_TASK_ID % 16)) # This is the experiment
    SCENARIO_NUM=$(($SLURM_ARRAY_TASK_ID / 16)) # This is the scenario
    SCENARIOS=(${SCENARIOS_LIST[$SCENARIO_NUM]})

    TASK="exp"
    SIERRA_CMD="$SIERRA_BASE_CMD --hpc-env=slurm --exp-range=$EXP_NUM:$EXP_NUM --exec-resume"
    echo "********************************************************************************\n"
    squeue -j $SLURM_ARRAY_TASK_ID -o "%.9i %.9P %.8j %.8u %.2t %.10M %.6D %S %e"
    echo "********************************************************************************\n"

else
    SCENARIOS=("${SCENARIOS_LIST[@]}")
    TASK="$1"
    SIERRA_CMD="$SIERRA_BASE_CMD \
                 --hpc-env=local\
                 --no-verify-results\
                 --exp-graphs=inter\
                 --plot-large-text\
                 --physics-n-engines=4\
                 --plot-log-xscale\
                 --plot-log-yscale
                 "
fi

cd $SIERRA_ROOT

if [ "$TASK" == "exp" ] || [ "$TASK" == "all" ]; then

    for s in "${SCENARIOS[@]}"
    do
        $SIERRA_CMD --scenario=$s \
                  --batch-criteria population_density.${DENSITY}.${SIZEINC}.${CARDINALITY}
    done
fi

if [ "$TASK" == "comp" ] || [ "$TASK" == "all" ]; then
    criteria=population_density.CD1p0.${SIZEINC}.${CARDINALITY}

    $SIERRA_CMD --scenario=$s \
              --pipeline 5\
              --batch-criteria $criteria\
              --bc-univar\
              --scenario-comparison\
              --scenarios-list=SS.16x8x2,DS.16x8x2\
              --scenarios-legend="SS","DS"

    $SIERRA_CMD --scenario=$s \
              --pipeline 5\
              --batch-criteria $criteria\
              --bc-univar\
              --scenario-comparison\
              --scenarios-list=RN.8x8x2,PL.8x8x2\
              --scenarios-legend="RN","PL"
fi
