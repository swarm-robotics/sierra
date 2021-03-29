#!/bin/bash -l
#SBATCH --time=24:00:00
#SBATCH --nodes 8
#SBATCH --tasks-per-node=12
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=2G
#SBATCH --mail-type=ALL
#SBATCH --mail-user=harwe006@umn.edu
#SBATCH --output=R-%x.%j.out
#SBATCH --error=R-%x.%j.err
#SBATCH -J 2021-tro-sc2

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
--env ARGOS_PLUGIN_PATH --env LOG4CXX_CONFIGURATION"

################################################################################
# Begin Experiments                                                            #
################################################################################
OUTPUT_ROOT=$HOME/exp/2021-tro-sc2-2
DENSITY=5p0
N_BLOCKS=4000
BLOCK_DIST=PL
XCARDINALITY1=8
XCARDINALITY2=3
YCARDINALITY1=4
YCARDINALITY2=8
TIME=time_setup.T50000
TASKS=("scalability" "flexibility" "robustness_pd" "robustness_saa")
NSIMS=96
CONTROLLERS_LIST=(d0.CRW d0.DPO d1.BITD_DPO d2.BIRTD_DPO)

SIERRA_BASE_CMD="python3 sierra.py \
                  --sierra-root=$OUTPUT_ROOT\
                  --template-input-file=$SIERRA_ROOT/templates/2021-tro-sc2.argos \
                  --n-sims=$NSIMS\
                  --pipeline 1 2\
                  --exp-graphs=inter\
                  --project=fordyca\
                  --dist-stats=conf95\
                  --exp-overwrite\
                  --exp-graphs=inter --project-no-yaml-LN\
                  --models-disable\
                  --with-robot-leds\
                  --log-level=DEBUG --exec-resume\
                  "

if [ -n "$MSIARCH" ] # Running on MSI
then

    # 4 controllers, 4 tasks
    TASK_NUM=$(($SLURM_ARRAY_TASK_ID % 4)) # This is the experiment
    CONTROLLER_NUM=$(($SLURM_ARRAY_TASK_ID / 4)) # This is the scenario
    CONTROLLERS=(${CONTROLLERS_LIST[$CONTROLLER_NUM]})
    TASK=${TASKS[$TASK_NUM]}

    SIERRA_CMD="$SIERRA_BASE_CMD --hpc-env=slurm"
    echo "********************************************************************************\n"
    squeue -j $SLURM_JOB_ID[$SLURM_ARRAY_TASK_ID] -o "%.9i %.9P %.8j %.8u %.2t %.10M %.6D %S %e"
    echo "********************************************************************************\n"

else
    CONTROLLERS=("${CONTROLLERS_LIST[@]}")
    TASK="$1"

    SIERRA_CMD="$SIERRA_BASE_CMD\
                  --hpc-env=local\
                  --physics-n-engines=2\
                  --no-verify-results\
                  --plot-large-text\
                  --plot-log-xscale"
fi

cd $SIERRA_ROOT

# Scalability/emergence analysis
if [ "$TASK" == "scalability" ] || [ "$TASK" == "emergence" ] || [ "$TASK" == "all" ]
then
    for c in "${CONTROLLERS[@]}"
    do
        $SIERRA_CMD --scenario=${BLOCK_DIST}.16x16x2 \
                  --batch-criteria population_density.CD${DENSITY}.I16.C${XCARDINALITY1} block_motion_dynamics.C${YCARDINALITY1}.F25p0.RW0p001\
                  --controller=${c} \
                  --n-blocks=${N_BLOCKS}\
                  --time-setup=${TIME}

    done
fi

# Flexibility analysis.
if [ "$TASK" == "flexibility" ] || [ "$TASK" == "all" ]
then
    for c in "${CONTROLLERS[@]}"
    do
        $SIERRA_CMD --scenario=${BLOCK_DIST}.16x16x2 \
                  --batch-criteria population_density.CD${DENSITY}.I32.C${XCARDINALITY2} temporal_variance.MSine\
                  --controller=${c}\
                  --n-blocks=${N_BLOCKS}\
                  --plot-primary-axis=1\
                  --time-setup=${TIME}

    done
fi

# Robustness analysis.
if [ "$TASK" == "robustness_saa" ] || [ "$TASK" == "all" ]
then
    for c in "${CONTROLLERS[@]}"
    do
        $SIERRA_CMD --scenario=${BLOCK_DIST}.16x16x2 \
                    --batch-criteria population_density.CD${DENSITY}.I32.C${XCARDINALITY2} saa_noise.all.C${YCARDINALITY2}\
                    --controller=${c} \
                    --n-blocks=${N_BLOCKS}\
                    --plot-primary-axis=1\
                    --time-setup=${TIME}
    done
fi

if [ "$TASK" == "robustness_pd" ] || [ "$TASK" == "all" ]
then
    for c in "${CONTROLLERS[@]}"
    do
        $SIERRA_CMD --scenario=${BLOCK_DIST}.16x16x2 \
                  --batch-criteria population_density.CD${DENSITY}.I32.C${XCARDINALITY2} population_dynamics.C${YCARDINALITY2}.F2p0.D0p0001 \
                  --controller=${c} \
                  --n-blocks=${N_BLOCKS}\
                  --plot-primary-axis=1\
                  --time-setup=${TIME}
    done
fi

if [ "$TASK" == "comp" ] || [ "$TASK" == "all" ]
then
    STAGE5_CMD="python3 sierra.py \
                  --project=fordyca\
                  --pipeline 5\
                  --controller-comparison\
                  --comparison-type=LNraw\
                  --plot-large-text\
                  --plot-log-xscale\
                  --dist-stats=conf95\
                  --bc-bivar\
                  --sierra-root=$OUTPUT_ROOT"

    # Generate scalability/emergence comparison graphs
    $STAGE5_CMD --batch-criteria population_density.CD${DENSITY}.I32.C${XCARDINALITY1} block_motion_dynamics.C${YCARDINALITY1}.F25p0.RW0p001\
                    --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                    --controllers-legend CRW,DPO,STOCHM,STOCHX

    # Generate flexibility comparison graphs
    $STAGE5_CMD --batch-criteria population_density.CD${DENSITY}.I32.C${XCARDINALITY2} temporal_variance.MSine\
                --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                    --controllers-legend CRW,DPO,STOCHM,STOCHX

    # Generate robustness comparison graphs
    $STAGE5_CMD --batch-criteria population_density.CD${DENSITY}.I32.C${XCARDINALITY2} population_dynamics.C${YCARDINALITY2}.F2p0.D0p0001 \
                --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                --controllers-legend CRW,DPO,STOCHM,STOCHX

    $STAGE5_CMD --batch-criteria population_density.CD${DENSITY}.I32.C${XCARDINALITY2} saa_noise.all.C${YCARDINALITY2}\
                --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                --controllers-legend CRW,DPO,STOCHM,STOCHX


fi
