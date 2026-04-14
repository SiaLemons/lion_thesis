# LabGym i AI-LAB
Undervejs vil der stå DITBRUGERNAVN dette er din grimme mail uden @student.aau.dk
## Hvad denne guide antager
Denne guide antager:
- man har allerede en **trænet detector** eksporteret fra LabGym
- man har allerede en **trænet categorizer** eksporteret fra LabGym
- videoer ligger som `.mp4`
- man vil køre **headless** uden GUI
- man vil bruge **array jobs** på AI-LAB
- man vil **ikke** generere annoteret video
## Tjek analyzebehavior_dt.py
Tjek analyzebehavior_dt.py fra teams for mappe problem
Åben analyzebehavior_dt.py
Find: `self.results_path=`
hvis der står:
```python
self.results_path=os.path.join(results_path,os.path.splitext(self.basename)[0])
```
ændre til:
```python
self.results_path=results_path
```
## Opsætning
### TRIN 1 — Log ind på AI-LAB (fra Windows)
Åbn **PowerShell** og skriv:
```bash
ssh ailab-1
```
eller
```bash
ssh ailab-2
```

### TRIN 2 — Opret mapper
Når du er logget ind:
```bash
mkdir -p ~/labgym_lion/{code,data/videos,data/models,results,logs}
```

Den skal ende sådan:
```
~/labgym_lion/  
├── code/  
├── data/  
│   ├── videos/  
│   └── models/  
├── results/  
└── logs/
```

Læg derefter:
- test videoer i `~/labgym_lion/data/videos/`
	- Dette er kun videoer til at test om det hele virker. Selve analysen tager videoerne fra preprocessing output folder
- detector-mappen i `~/labgym_lion/data/models/
- categorizer-mappen i `~/labgym_lion/data/models/`
### TRIN 3 — Lav virtual environment i Python-containeren
Kør:
```bash
srun --mem=8G --cpus-per-task=2 \
singularity exec /ceph/container/python/python_3.10.sif \
python -m venv --system-site-packages ~/labgym_lion/venv
```

### TRIN 4 — Hent LabGym-koden
Gå til kode mappen:
```bash
cd ~/labgym_lion/code
```

Hent LabGym source code:
```bash
git clone https://github.com/umyelab/LabGym.git
```

### TRIN 5 — Fjern GUI-afhængigheden
Åben pyproject.toml i LabGym
```bash
nano ~/labgym_lion/code/LabGym/pyproject.toml
```
Find `wxPython` i dependencies og fjern den.
Gem (Ctrl+s) og luk (Ctrl+x)

### TRIN 6 — Indsæt analyzebehavior_dt.py fra teams
Åben WinSCP og gå til `~/labgym_lion/code/LabGym/LabGym`
Omdøb `analyzebehavior_dt.py` til `analyzebehavior_dt_old.py`
Lig `analyzebehavior_dt.py` fra teams og ind i mappen

### TRIN 6 — Installér LabGym i venv inde i containeren
Kør:
```Bash
srun --mem=24G --cpus-per-task=8 --time=02:00:00 --pty bash
```
og derefter:
```bash
singularity exec \
-B ~/labgym_lion:/scratch/labgym_lion \
-B $HOME/.singularity:/scratch/singularity \
/ceph/container/python/python_3.10.sif \
/bin/bash -c "
export TMPDIR=/scratch/singularity/tmp
source /scratch/labgym_lion/venv/bin/activate

python -m pip install --upgrade pip setuptools wheel

cd /scratch/labgym_lion/code/LabGym
pip install -e . --no-deps

pip install --no-cache-dir numpy==1.26.4
pip install --no-cache-dir tensorflow==2.15.1

pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless
pip install --no-cache-dir opencv-python-headless==4.10.0.84

pip install --no-cache-dir pandas openpyxl scikit-image matplotlib pillow pyyaml tqdm

pip install --no-cache-dir \
  torch torchvision torchaudio \
  cloudpickle fvcore iopath hydra-core omegaconf ninja pycocotools \
  scikit-learn scikit-posthocs seaborn tabulate tomli xlsxwriter yacs requests
"
```

Bemærk at der VIL komme warnings og errors når vi installere, tester og bruger LabGym da vi ikke bruger det som det er lavet.
### TRIN 7 — Test at installationen virker
Kør:
```bash
singularity exec --nv \
-B ~/labgym_lion:/scratch/labgym_lion \
/ceph/container/python/python_3.10.sif \
/bin/bash -c "
source /scratch/labgym_lion/venv/bin/activate
python - <<'PY'
import numpy
print('numpy:', numpy.__version__)

import cv2
print('cv2 works')

import torch
print('torch:', torch.__version__)
print('torch cuda available:', torch.cuda.is_available())

from LabGym.analyzebehavior_dt import AnalyzeAnimalDetector
print('OK - LabGym detector API works')
PY
"
```

Der kommer måske warnings og errors men så længe der kommer til at stå 'OK - LabGym detector API works' så virker LabGym

Det interaktive job kan nu lukkes med:
```bash
scancel JOBID
```
Erstat JOBID med det interaktive jobs id som kan findes ved at bruge:
```bash
squeue --me
```

### TRIN 8 — Opret Python-wrapper-script
Lav filen:
```bash
nano ~/labgym_lion/code/run_labgym_detector.py
```

Indsæt dette i filen:
```bash
import argparse
import ast
import csv
from pathlib import Path

from LabGym.analyzebehavior_dt import AnalyzeAnimalDetector


def parse_animal_number(raw_value, animal_kinds):
    raw_value = str(raw_value).strip()

    if raw_value.isdigit():
        return int(raw_value)

    parsed = ast.literal_eval(raw_value)

    if isinstance(parsed, int):
        return parsed

    if isinstance(parsed, dict):
        return {str(k): int(v) for k, v in parsed.items()}

    if isinstance(parsed, (list, tuple)):
        if len(parsed) != len(animal_kinds):
            raise ValueError(
                f"--animal-number as a list must have the same length as --animal-kinds. "
                f"Got {len(parsed)} values but {len(animal_kinds)} classes."
            )
        return {animal_kinds[i]: int(parsed[i]) for i in range(len(animal_kinds))}

    raise ValueError("--animal-number must be an integer, dict, or list.")


def read_categorizer_table(categorizer_dir):
    mp = Path(categorizer_dir) / "model_parameters.txt"
    if not mp.exists():
        raise FileNotFoundError(f"Could not find model_parameters.txt in {categorizer_dir}")

    with mp.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("model_parameters.txt exists but contains no rows.")

    return rows


def build_names_and_colors(behavior_names):
    default_pairs = [
        ["#ffffff", "#ff00ff"],
        ["#ffffff", "#00ffff"],
        ["#ffffff", "#00ff00"],
        ["#ffffff", "#ff9900"],
        ["#ffffff", "#ff0000"],
        ["#ffffff", "#0000ff"],
        ["#ffffff", "#9900ff"],
        ["#ffffff", "#999999"],
    ]

    names_and_colors = {}
    for i, name in enumerate(behavior_names):
        names_and_colors[name] = default_pairs[i % len(default_pairs)]
    return names_and_colors


def build_id_colors(animal_number):
    default_colors = [
        (255, 255, 255),
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 255, 255),
        (255, 128, 0),
        (128, 0, 255),
        (128, 128, 128),
    ]

    if isinstance(animal_number, int):
        total = animal_number
    elif isinstance(animal_number, dict):
        total = sum(animal_number.values())
    else:
        raise ValueError("animal_number must be int or dict")

    return [default_colors[i % len(default_colors)] for i in range(total)]


def first_int(rows, key, default):
    value = rows[0].get(key, default)
    try:
        return int(value)
    except Exception:
        return default


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--detector", required=True)
    parser.add_argument("--categorizer", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--animal-number", required=True)
    parser.add_argument("--animal-kinds", nargs="+", required=True)

    parser.add_argument("--behavior-mode", type=int, default=None)
    parser.add_argument("--framewidth", type=int, default=0)
    parser.add_argument("--dim-tconv", type=int, default=None)
    parser.add_argument("--dim-conv", type=int, default=None)
    parser.add_argument("--channel", type=int, default=None)
    parser.add_argument("--include-bodyparts", action="store_true")
    parser.add_argument("--std", type=int, default=None)
    parser.add_argument("--start-time", type=float, default=0)
    parser.add_argument("--duration", type=float, default=0)
    parser.add_argument("--length", type=int, default=None)
    parser.add_argument("--social-distance", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--background-free", action="store_true")
    parser.add_argument("--uncertain", type=int, default=0)
    parser.add_argument("--skip-annotated-video", action="store_true")

    args = parser.parse_args()

    results = Path(args.results)
    results.mkdir(parents=True, exist_ok=True)

    animal_number = parse_animal_number(args.animal_number, args.animal_kinds)

    rows = read_categorizer_table(args.categorizer)

    behavior_names = [row["classnames"] for row in rows if row.get("classnames")]
    if not behavior_names:
        raise ValueError("Could not extract behavior names from the 'classnames' column.")

    dim_tconv = args.dim_tconv if args.dim_tconv is not None else first_int(rows, "dim_tconv", 8)
    dim_conv = args.dim_conv if args.dim_conv is not None else first_int(rows, "dim_conv", 8)
    channel = args.channel if args.channel is not None else first_int(rows, "channel", 1)
    length = args.length if args.length is not None else first_int(rows, "time_step", 15)
    std = args.std if args.std is not None else first_int(rows, "std", 0)
    behavior_mode = args.behavior_mode if args.behavior_mode is not None else first_int(rows, "behavior_kind", 0)
    social_distance = args.social_distance if args.social_distance is not None else first_int(rows, "social_distance", 0)
    network = first_int(rows, "network", 1)
    animation_analyzer = network != 0

    names_and_colors = build_names_and_colors(behavior_names)
    id_colors = build_id_colors(animal_number)

    print("Parsed animal_number:", animal_number)
    print("Animal kinds:", args.animal_kinds)
    print("Behavior names:", behavior_names)
    print("dim_tconv:", dim_tconv)
    print("dim_conv:", dim_conv)
    print("channel:", channel)
    print("length:", length)
    print("behavior_mode:", behavior_mode)
    print("social_distance:", social_distance)
    print("ID colors:", id_colors)

    aad = AnalyzeAnimalDetector()

    aad.prepare_analysis(
        args.detector,
        args.video,
        args.results,
        animal_number,
        args.animal_kinds,
        behavior_mode,
        names_and_colors=names_and_colors,
        framewidth=None if args.framewidth == 0 else args.framewidth,
        dim_tconv=dim_tconv,
        dim_conv=dim_conv,
        channel=channel,
        include_bodyparts=args.include_bodyparts,
        std=std,
        categorize_behavior=True,
        animation_analyzer=animation_analyzer,
        t=args.start_time,
        duration=args.duration,
        length=length,
        social_distance=social_distance,
    )

    aad.acquire_information(
        batch_size=args.batch_size,
        background_free=args.background_free
    )

    if behavior_mode != 1:
        aad.craft_data()

    aad.categorize_behaviors(
        args.categorizer,
        uncertain=args.uncertain
    )

    if not args.skip_annotated_video:
        aad.annotate_video(
            ID_colors=id_colors,
            animal_to_include=args.animal_kinds,
            behavior_to_include=behavior_names,
            show_legend=True
        )

    aad.export_results(
        normalize_distance=True,
        parameter_to_analyze=[
            "count",
            "duration",
            "latency",
            "3 length parameters",
            "3 areal parameters",
            "4 locomotion parameters",
        ]
    )

    print("Done.")


if __name__ == "__main__":
    main()
```
Gem (Ctrl+s) og luk (Ctrl+x)

### TRIN 9 — Lav array job script
Videoerne til analyse skal nu ligge inde i mappen til videoer. Til at starte med kan man have et par meget korte test videoer.

Lav en array script:
```bash
nano ~/labgym_lion/code/run_labgym_array.sh
```

Indsæt:
```bash
#!/bin/bash
#SBATCH --job-name=labgym_lion
#SBATCH --output=/ceph/home/student.aau.dk/DITBRUGERNAVN/labgym_lion/logs/labgym_%A_%a.out
#SBATCH --error=/ceph/home/student.aau.dk/DITBRUGERNAVN/labgym_lion/logs/labgym_%A_%a.err
#SBATCH --mem=24G
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --time=08:00:00

set -euo pipefail

BASE=/ceph/home/student.aau.dk/DITBRUGERNAVN/labgym_lion
VIDEO_LIST=${BASE}/code/video_list.txt

FILE=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "${VIDEO_LIST}")

if [ -z "${FILE}" ]; then
    echo "No video found"
    exit 1
fi

BASENAME=$(basename "${FILE}" .mp4)
RESULTS_DIR=/scratch/labgym_lion/results/${BASENAME}

singularity exec --nv \
-B ${BASE}:/scratch/labgym_lion \
/ceph/container/python/python_3.10.sif \
/bin/bash -c "
source /scratch/labgym_lion/venv/bin/activate

mkdir -p '${RESULTS_DIR}'

python /scratch/labgym_lion/code/run_labgym_detector.py \
  --video '${FILE}' \
  --detector /scratch/labgym_lion/data/models/lion_detector_collectively_v3 \
  --categorizer /scratch/labgym_lion/data/models/lion_cat_v7 \
  --results '${RESULTS_DIR}' \
  --animal-number '{\"Male\": 1, \"Female\": 2}' \
  --animal-kinds Male Female \
  --batch-size 16 \
  --uncertain 20 \
  --duration 0 \
  --skip-annotated-video
"
```

Vigtige ting at ændre:

- DITBRUGERNAVN
- `--animal-number` til hvor mange individer man gerne vil finde i hver class
- `--animal-kinds` til hvilke classes man gerne vil finde

### TRIN 10 — Lav submit script
```bash
nano ~/labgym_lion/code/submit_array.sh
```

Indsæt:
```bash
#!/bin/bash

PROJECT_DIR=$HOME/labgym_lion
INPUT_DIR=/ceph/home/student.aau.dk/DITBRUGERNAVN/video_processing/data_out
FILE_LIST=$PROJECT_DIR/code/video_list.txt
JOB_SCRIPT=$PROJECT_DIR/code/run_labgym_array.sh

mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/results"

find "$INPUT_DIR" -maxdepth 1 -type f -name "*.mp4" | sort > "$FILE_LIST"

NUM_FILES=$(wc -l < "$FILE_LIST")

if [ "$NUM_FILES" -eq 0 ]; then
    echo "No MP4 files found"
    exit 1
fi

MAX_INDEX=$((NUM_FILES - 1))

echo "Found $NUM_FILES videos"
echo "Submitting jobs (max 8 at a time)..."

sbatch --array=0-"$MAX_INDEX"%8 "$JOB_SCRIPT"
```

ændre DITBRUGERNAVN til dit brugernavn
### TRIN 11 — Gør scripts kørbare
```Bash
chmod +x ~/labgym_lion/code/run_labgym_array.sh
```
```bash
chmod +x ~/labgym_lion/code/submit_array.sh
```
## Brug LabGym
### Sådan kører man array-jobbet
Send jobbet:

```bash
sbatch ~/labgym_lion/code/submit_array.sh
```

Tjek køen:

```bash
squeue --me
```

### Hvor finder man output?
Hver video får sin egen resultatmappe:

```bash
~/labgym_lion/results/video_navn/
```

hver array-task får sin egen log:

```bash
~/labgym_lion/logs/labgym_JOBID_TASKID.out  
~/labgym_lion/logs/labgym_JOBID_TASKID.err
```