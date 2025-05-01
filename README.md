# autonarrate
The AutoNarrate workflow systematically transforms PowerPoint slide content into a professional, AI-driven narrated video.


## Implementation Guide

Follow these steps to deploy the workflow:

1. **Clone the source code from GitHub**:
   ```bash
   git clone https://github.com/mail2mhossain/autonarrate.git
   cd autonarrate
   ```

2. **Create a Conda environment (Assuming Anaconda is installed):**:
   ```bash
   conda create -n autonarrate_env python=3.11
   ```

3. **Activate the environment**:
   ```bash
   conda activate autonarrate_env
   ```

4. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the app**:
   ```bash
   python desktop_app.py
   ```

To remove the environment when done:
```bash
conda remove --name autonarrate_env --all
```