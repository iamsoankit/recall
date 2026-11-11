from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent


def main() -> None:
    subprocess.run(["npm", "ci", "--prefix", str(ROOT / "web")], check=True)
    subprocess.run(["npm", "run", "build", "--prefix", str(ROOT / "web")], check=True)


if __name__ == "__main__":
    main()
