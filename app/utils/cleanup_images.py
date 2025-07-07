# cleanup_images.py
from pathlib import Path
from image_utils import standardize_filename
import shutil

def reorganize_images(root_path="static/images/devices"):
    device_path = Path(root_path)
    
    # First move all loose files to manufacturer folders
    for image_file in device_path.glob('*.jpg'):
        if '-' in image_file.name:
            manufacturer = image_file.name.split('-')[0].capitalize()
            target_dir = device_path / manufacturer
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(image_file), str(target_dir / image_file.name))
    
    # Then standardize all filenames
    for manufacturer_dir in device_path.iterdir():
        if manufacturer_dir.is_dir():
            for image_file in manufacturer_dir.glob('*.jpg'):
                # Parse current filename (imperfect but works for most cases)
                parts = image_file.stem.split('-')
                model_part = '-'.join(parts[1:])  # Everything after manufacturer
                
                new_name = standardize_filename(
                    manufacturer=manufacturer_dir.name,
                    model=model_part
                )
                
                if new_name != image_file.name:
                    new_path = image_file.with_name(new_name)
                    image_file.rename(new_path)
                    print(f"Renamed: {image_file.name} -> {new_name}")

if __name__ == '__main__':
    reorganize_images()