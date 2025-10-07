
from src.module.demo import demo
import os

# Determine the base directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# build the absolute paths to the needed utilities.
dir_model = os.path.join(BASE_DIR, './model/modelo_entrenado.pkl')
dir_audio = os.path.join(BASE_DIR, './audio/')

# Normalize the paths to ensure compatibility across different operating systems
dir_model = os.path.normpath(dir_model)
dir_audio = os.path.normpath(dir_audio)

# Call demo 
demo(dir_model, dir_audio)