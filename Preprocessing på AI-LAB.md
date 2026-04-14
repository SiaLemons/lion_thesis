# Preprocessing På AI-LAB
## Oversigt
Du vil:
1. Logge ind på Aalborg University’s AI-LAB
2. Uploade dine videoer og script
3. Bruge en eksisterende Python-container
4. Køre et batch job med Slurm
5. Få færdige videoer ud

## Mappe Overblik
Du kommer til at have denne struktur:
```
video_processing/
│
├── code/          → dit Python script
├── data_in/       → dine videoer
├── data_out/      → færdige videoer
├── logs/          → output + fejl
└── tools/         → ffmpeg
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
mkdir -p ~/video_processing/{code,data_in,data_out,logs,tools}
```

### TRIN 3 — Installer ffmpeg
På AI-LAB:
Gå til tools mappen
```bash
cd ~/video_processing/tools
```
Hent ffmpeg
```bash
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
```
Installer ffmpeg
```bash
tar -xf ffmpeg-release-amd64-static.tar.xz
```
tjek installationen
```
~/video_processing/tools/ffmpeg-7.0.2-amd64-static/ffmpeg -version
```
Hvis du ser versioner er ffmpeg installerert

### TRIN 4 — Upload script (fra din computer)
1. Uploade lion_thesis_training_preprocess.py fra Teams til ~/video_processing/code/ ved brug af WinSCP
	- Man kan trække filer fra egen stifinder og ind i programmet
2. Uploade videoer i ~/video_processing/data_in/
	- Start med en test video til at teste installationen
### TRIN 5 — Test script
Kør:
``` bash
srun singularity exec /ceph/container/python/python_3.13.sif \
python3 ~/video_processing/code/lion_thesis_training_preprocess.py \
  --input_file ~/video_processing/data_in/DIN_VIDEO.avi \
  --output_dir ~/video_processing/data_out \
  --ffmpeg_path ~/video_processing/tools/ffmpeg-7.0.2-amd64-static/ffmpeg
```
Ændre DIN_VIDEO til den video som du har lagt ind

### TRIN 6 — Lav batch job
Lav batch job fil:
```bash
nano ~/video_processing/code/run_array.sh
```

Indsæt i filen (ændre BRUGERNAVN til dit eget bruger navn (uden @student.aau.dk)):
```bash
#!/bin/bash
#SBATCH --job-name=video_array
#SBATCH --output=/ceph/home/student.aau.dk/DITBRUGERNAVN/video_processing/logs/pre_%A_%a.out
#SBATCH --error=/ceph/home/student.aau.dk/DITBRUGERNAVN/video_processing/logs/pre_%A_%a.err
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

PROJECT_DIR=~/video_processing

PY_CONTAINER=/ceph/container/python/python_3.13.sif
SCRIPT=$PROJECT_DIR/code/lion_thesis_training_preprocess.py
FILE_LIST=$PROJECT_DIR/file_list.txt
OUTPUT_DIR=$PROJECT_DIR/data_out
FFMPEG_PATH=$(echo $PROJECT_DIR/tools/ffmpeg-7.0.2-amd64-static/ffmpeg)

mkdir -p "$OUTPUT_DIR"
mkdir -p "$PROJECT_DIR/logs"

FILE=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$FILE_LIST")

echo "Array task ID: $SLURM_ARRAY_TASK_ID"
echo "Processing file: $FILE"

singularity exec "$PY_CONTAINER" python3 "$SCRIPT" \
  --input_file "$FILE" \
  --output_dir "$OUTPUT_DIR" \
  --ffmpeg_path "$FFMPEG_PATH"
```

Gem (Ctrl+s) og luk (Ctrl+x).

Lav et submit script som automatisk finder antal af videoer i video mappen
```bash
nano ~/video_processing/code/submit_array.sh
```

Indsæt:

```bash
#!/bin/bash

PROJECT_DIR=~/video_processing
INPUT_DIR=$PROJECT_DIR/data_in
FILE_LIST=$PROJECT_DIR/file_list.txt
JOB_SCRIPT=$PROJECT_DIR/code/run_array.sh

mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data_out"

find "$INPUT_DIR" -maxdepth 1 -type f -name "*.avi" | sort > "$FILE_LIST"

NUM_FILES=$(wc -l < "$FILE_LIST")

if [ "$NUM_FILES" -eq 0 ]; then
    echo "No AVI files found"
    exit 1
fi

MAX_INDEX=$((NUM_FILES - 1))

echo "Found $NUM_FILES AVI files"
echo "Submitting array job: 0-$MAX_INDEX"

sbatch --array=0-"$MAX_INDEX"%8 "$JOB_SCRIPT"
```
`%8` = max 8 jobs samtidig. Kan ændres hvis det giver mening

Gem (Ctrl+s) og luk (Ctrl+x).

### TRIN 7 — Gør scriptet kørbart
```bash
chmod +x ~/video_processing/code/run_array.sh
```
```bash
chmod +x ~/video_processing/code/submit_array.sh
```

## Brug scriptet
### TRIN 1 — Kør job
```bash
sbatch ~/video_processing/code/submit_array.sh
```

### TRIN 2 — Tjek job
```bash
squeue --me
```

### TRIN 3 — Tjek logs
Ændre JOBID til det ID som man får når man starter et batch job

Brug denne til at læse terminal log:
```bash
cat ~/video_processing/logs/pre_JOBID.out
```

Brug denne til at læse error log:
```bash
cat ~/video_processing/logs/pre_JOBID.out
```

Eller læs dem i WinSCP
### TRIN 4 — Find dine videoer
i terminalen kan du bruge:
```bash
ls ~/video_processing/data_out
```
eller tjek WinSCP. WinSCP skal genopfriskes ved brug af enten den grønne knap i højre side eller med Ctrl+r


