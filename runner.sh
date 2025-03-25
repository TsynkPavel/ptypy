#!/bin/bash

# -----------------------------------------------------------

LOG_FILE="runner.log"

exec > >(tee -a "${LOG_FILE}") 2>&1

# Проверяем, находимся ли уже в виртуальном окружении
if [ -z "${VIRTUAL_ENV}" ]; then
    echo "Активируем виртуальное окружение..."
    source ".venv/bin/activate"
else
    echo "Уже в виртуальном окружении."
fi

# -----------------------------------------------------------

PYTHON_FILE="brick_512_512_2layer_CuSi.py"
DRAWER_FILE="my_ptyr_reader.py"
SENDER_FILE="bot.py"

args_to_path() {
    local args="$1"
    echo "$args" | sed -E 's/--//g; s/=/_/g; s/ /\//g'
}

# -----------------------------------------------------------

# args="--steps=5 --spacing=1e-6"
# path_to_result=$(args_to_path "$args")
# python_file_without_extention=$(echo "${PYTHON_FILE}" | sed -E "s/.py//g")
# ptyr_file_path=${python_file_without_extention}_DM_cupy_0100.ptyr

# python ${PYTHON_FILE} ${args}
# python ${DRAWER_FILE} --subfolder="results/${path_to_result}" --ptyr-file="results/${path_to_result}/recons/${python_file_without_extention}/"${ptyr_file_path}
# python ${SENDER_FILE} --folder="results/${path_to_result}/CMRmap"

# -----------------------------------------------------------

python ptypy_i13_AuStar_focused-x2_Damir_orig.py