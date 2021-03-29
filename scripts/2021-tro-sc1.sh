#!/bin/bash -l
#SBATCH --time=24:00:00
#SBATCH --nodes 1
#SBATCH --tasks-per-node=64
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=2G
#SBATCH --mail-type=ALL
#SBATCH --mail-user=harwe006@umn.edu
#SBATCH --output=R-%x.%j.out
#SBATCH --error=R-%x.%j.err
#SBATCH -J 2021-tro-sc1

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
OUTPUT_ROOT=$HOME/exp/2021-tro-sc1
TIME=time_setup.T50000

CONTROLLERS_LIST=(d0.CRW d0.DPO d1.BITD_DPO d2.BIRTD_DPO)
TASKS=("scalability" "flexibility" "robustness_saa" "robustness_pd")
CARDINALITY=C8
NSIMS=96

SIERRA_BASE_CMD="python3 sierra.py \
                  --sierra-root=$OUTPUT_ROOT\
                  --template-input-file=$SIERRA_ROOT/templates/2021-tro-sc1.argos \
                  --n-sims=$NSIMS\
                  --pipeline 1 2\
                  --exp-graphs=inter --project-no-yaml-LN\
                  --project=fordyca\
                  --dist-stats=conf95\
                  --exp-overwrite\
                  --models-disable\
                  --with-robot-leds\
                  --log-level=DEBUG\
                  --no-verify-results
                  "

if [ -n "$MSIARCH" ] # Running on MSI
then
    # 4 controllers, 4 tasks
    TASK_NUM=$(($SLURM_ARRAY_TASK_ID % 4)) # This is the task
    CONTROLLER_NUM=$(($SLURM_ARRAY_TASK_ID / 4)) # This is the controller
    CONTROLLERS=(${CONTROLLERS_LIST[$CONTROLLER_NUM]})
    TASK=${TASKS[$TASK_NUM]}


    SIERRA_CMD="$SIERRA_BASE_CMD --hpc-env=slurm --exec-resume"

    echo "********************************************************************************\n"
    squeue -j $SLURM_JOB_ID[$SLURM_ARRAY_TASK_ID] -o "%.9i %.9P %.8j %.8u %.2t %.10M %.6D %S %e"
    echo "********************************************************************************\n"
else
    TASK="$1"
    CONTROLLERS=("${CONTROLLERS_LIST[@]}")

    SIERRA_CMD="$SIERRA_BASE_CMD\
                  --hpc-env=local\
                  --physics-n-engines=2
                  "
fi

cd $SIERRA_ROOT

# Scalability/emergence analysis
if [ "$TASK" == "scalability" ] || [ "$TASK" == "emergence" ] || [ "$TASK" == "all" ]
then
    for c in "${CONTROLLERS[@]}"
    do
        $SIERRA_CMD --scenario=SS.32x16x2 \
                    --batch-criteria population_size.Log128 \
                    --controller=${c} \
                    --n-blocks=512\
                    --time-setup=${TIME}

        $SIERRA_CMD --scenario=RN.48x48x2 \
                      --batch-criteria population_size.Log512 \
                      --controller=${c} \
                      --n-blocks=2048\
                      --time-setup=${TIME}
    done
fi

# Flexibility analysis
if [ "$TASK" == "flexibility" ] || [ "$TASK" == "all" ]
then
    for c in "${CONTROLLERS[@]}"
    do
        $SIERRA_CMD --scenario=SS.32x16x2 \
                    --batch-criteria temporal_variance.BCSquare.Z50 \
                    --controller=${c}\
                    --n-blocks=200\
                    --time-setup=${TIME}

        # $SIERRA_CMD --scenario=RN.48x48x2 \
        #               --batch-criteria temporal_variance.BCSquare.Z200\
        #               --controller=${c} \
        #               --n-blocks=800\
        #               --time-setup=${TIME}

    done
fi

# Robustness analysis
if [ "$TASK" == "robustness_saa" ] || [ "$TASK" == "all" ]
then
    for c in "${CONTROLLERS[@]}"
    do

        $SIERRA_CMD --scenario=SS.32x16x2 \
                    --batch-criteria saa_noise.all.${CARDINALITY}.Z50\
                    --controller=${c} \
                    --n-blocks=200\
                    --n-robots=50\
                    --time-setup=${TIME}

        $SIERRA_CMD --scenario=RN.48x48x2 \
                    --batch-criteria saa_noise.all.${CARDINALITY}.Z200\
                    --controller=${c} \
                    --n-blocks=800\
                    --n-robots=200\
                    --time-setup=${TIME}

    done
fi

if [ "$TASK" == "robustness_pd" ] || [ "$TASK" == "all" ]
then
    for c in "${CONTROLLERS[@]}"
    do
        # Steady state population of 5 when total swarm size is 50 (repair queue
        # steady state of 45)
        # rho = 45/46
        $SIERRA_CMD --scenario=SS.32x16x2 \
                    --batch-criteria population_dynamics.${CARDINALITY}.F1p0.M0p001.R0p001022222\
                    --controller=${c} \
                    --n-blocks=200\
                    --n-robots=50\
                    --time-setup=${TIME}

        # Steady state population of 20 when total swarm size is 200 (repair queue
        # steady state of 180)
        # rho = 180 / 181
        $SIERRA_CMD --scenario=RN.48x48x2 \
                    --batch-criteria population_dynamics.${CARDINALITY}.F1p0.M0p001.R0p001005556 \
                    --controller=${c} \
                    --n-blocks=800\
                    --n-robots=200\
                    --time-setup=${TIME}

    done
fi

if [ "$TASK" == "comp" ] || [ "$TASK" == "all" ]
then
    STAGE5_CMD="python3 sierra.py \
                  --project=fordyca\
                  --pipeline 5\
                  --controller-comparison\
                  --plot-large-text\
                  --plot-log-xscale\
                  --dist-stats=conf95\
                  --bc-univar\
                  --sierra-root=$OUTPUT_ROOT"

    # Generate scalability/emergence comparison graphs
    $STAGE5_CMD --batch-criteria population_size.Log128 \
                    --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                    --controllers-legend CRW,DPO,STOCHM,STOCHX

    $STAGE5_CMD --batch-criteria population_size.Log512 \
                    --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                    --controllers-legend CRW,DPO,STOCHM,STOCHX

    # Generate flexibility comparison graphs
    $STAGE5_CMD --batch-criteria temporal_variance.BCSquare.Z200\
                    --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                    --controllers-legend CRW,DPO,STOCHM,STOCHX

    $STAGE5_CMD --batch-criteria temporal_variance.BCSquare.Z50\
                    --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                    --controllers-legend CRW,DPO,STOCHM,STOCHX

    # Generate robustness comparison graphs
    $STAGE5_CMD --batch-criteria population_dynamics.${CARDINALITY}.F1p0.M0p001.R0p001022222\
                --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                --controllers-legend CRW,DPO,STOCHM,STOCHX

    $STAGE5_CMD --batch-criteria saa_noise.all.${CARDINALITY}.Z50\
                --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                --controllers-legend CRW,DPO,STOCHM,STOCHX

    $STAGE5_CMD --batch-criteria population_dynamics.${CARDINALITY}.F1p0.M0p001.R0p001005556 \
                --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                --controllers-legend CRW,DPO,STOCHM,STOCHX

    $STAGE5_CMD --batch-criteria saa_noise.all.${CARDINALITY}.Z200\
                --controllers-list d0.CRW,d0.DPO,d1.BITD_DPO,d2.BIRTD_DPO\
                --controllers-legend CRW,DPO,STOCHM,STOCHX


fi
