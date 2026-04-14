import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def parse_time_windows(filename):
    """Find all _stX_edY patterns and return (start, end) pairs."""
    matches = re.findall(r"_st(\d+)_ed(\d+)", filename)
    return [(int(start), int(end)) for start, end in matches]


def clean_filename(filename):
    """
    Removes all _stX_edY patterns from the filename stem.
    Example: 'mouse_st10_ed20_st40_ed60' -> 'mouse'
    """
    return re.sub(r"_st\d+_ed\d+", "", filename)


def ffmpeg_trim_and_convert(input_path, output_path, ffmpeg_path="ffmpeg", start=None, end=None):
    """Trim (if needed), resize, and convert to MP4 using ffmpeg."""
    ffmpeg_executable = shutil.which(ffmpeg_path) if ffmpeg_path == "ffmpeg" else ffmpeg_path

    if not ffmpeg_executable:
        print(f"FFmpeg not found: {ffmpeg_path}")
        return

    cmd = [ffmpeg_executable]

    if start is not None:
        cmd += ["-ss", str(start)]
    if end is not None:
        cmd += ["-to", str(end)]

    cmd += [
        "-i", str(input_path),
        "-vf", "scale=1280:-1,eq=brightness=-0.1:contrast=1.1",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-r", "10",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"FFmpeg failed on: {input_path}")
    except FileNotFoundError:
        print(f"Input file not found: {input_path}")


def main():
    parser = argparse.ArgumentParser(description="LabGym preprocessing script")
    parser.add_argument("--input_file", help="Single file to process")
    parser.add_argument("--output_dir", required=True, help="Path to output folder")
    parser.add_argument("--ffmpeg_path", required=True, help="Path to ffmpeg executable")
    args = parser.parse_args()

    print("LabGym Preprocessing Script")

    if not args.input_file:
        print("ERROR: --input_file is required for array jobs.")
        sys.exit(1)

    input_file = Path(args.input_file)
    out_path = Path(args.output_dir)

    if not input_file.is_file():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)

    out_path.mkdir(parents=True, exist_ok=True)

    files = [input_file]

    print(f"Found {len(files)} AVI file.\n")

    for file in files:
        base_name = file.stem
        time_windows = parse_time_windows(base_name)
        cleaned_name = clean_filename(base_name)

        if time_windows:
            print(f"{file.name}: Detected {len(time_windows)} window(s)")
            for i, (start, end) in enumerate(time_windows, 1):
                output_name = f"{cleaned_name}_trim{i}.mp4"
                output_file = out_path / output_name
                print(f"Trimming {file.name} ({start}s-{end}s)")
                ffmpeg_trim_and_convert(
                    file,
                    output_file,
                    ffmpeg_path=args.ffmpeg_path,
                    start=start,
                    end=end,
                )
                print(f"Saved: {output_name}")
        else:
            output_name = f"{cleaned_name}.mp4"
            output_file = out_path / output_name
            print(f"Converting full video: {file.name}")
            ffmpeg_trim_and_convert(
                file,
                output_file,
                ffmpeg_path=args.ffmpeg_path,
            )
            print(f"Saved: {output_name}")

    print("\nAll videos processed successfully! Filenames cleaned of _st/_ed tags.")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    main()