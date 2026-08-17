import os
import shutil
import numpy as np

# Fixed path string with raw string
dataset_path = r'C:\Users\SAMVIDA S\PlantDiseaseDetection\PlantVillage_dataset\color'

# Directories for training and validation
train_dir = 'train'
val_dir = 'val'

# Create train/val directories
os.makedirs(train_dir, exist_ok=True)
os.makedirs(val_dir, exist_ok=True)

# Go through each disease folder
for disease_folder in os.listdir(dataset_path):
    disease_folder_path = os.path.join(dataset_path, disease_folder)

    if os.path.isdir(disease_folder_path):
        train_disease_path = os.path.join(train_dir, disease_folder)
        val_disease_path = os.path.join(val_dir, disease_folder)

        os.makedirs(train_disease_path, exist_ok=True)
        os.makedirs(val_disease_path, exist_ok=True)

        for img in os.listdir(disease_folder_path):
            img_path = os.path.join(disease_folder_path, img)

            # Skip if source and destination are same
            if os.path.exists(img_path) and os.path.isfile(img_path):
                if np.random.rand() < 0.8:
                    dest_path = os.path.join(train_disease_path, img)
                else:
                    dest_path = os.path.join(val_disease_path, img)

                # Skip if destination file already exists
                if os.path.abspath(img_path) != os.path.abspath(dest_path):
                    try:
                        shutil.copy(img_path, dest_path)
                    except PermissionError:
                        print(f"Permission denied: {img_path}")
                    except Exception as e:
                        print(f"Error copying {img_path}: {e}")