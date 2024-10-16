import os
import subprocess
import shutil
import sys

def install_font(font_path: str) -> bool:
    """
    Install a font file to the system's font directory and update the font cache.

    Args:
        font_path (str): The path to the font file to be installed.

    Returns:
        bool: True if the font was successfully installed, False otherwise.
    """
    try:
        if not os.path.isfile(font_path):
            print(f"Font file not found: {font_path}")
            return False

        dest_dir = "/usr/share/fonts/truetype/custom_fonts"
        os.makedirs(dest_dir, exist_ok=True)

        font_name = os.path.basename(font_path)
        dest_path = os.path.join(dest_dir, font_name)
        shutil.copy(font_path, dest_path)
        print(f"Copied {font_name} to {dest_path}")

        subprocess.run(["sudo", "fc-cache", "-f", "-v"], check=True)
        print("Font cache updated.")

        result = subprocess.run(["fc-list", "|", "grep", font_name], capture_output=True, text=True, shell=True)
        if font_name in result.stdout:
            print(f"Font {font_name} installed successfully!")
            return True
        else:
            print(f"Font {font_name} installation failed.")
            return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python install_font.py /path/to/your/font.ttf")
        sys.exit(1)

    font_path = sys.argv[1]
    if install_font(font_path):
        sys.exit(0)
    else:
        sys.exit(1)
