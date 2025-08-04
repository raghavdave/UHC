### UHC Technical Assessment

All the codes and results are replicable.

__Order of execution:__

1. **00_data_load.py:** Python script creates project folder, downloads zip file from internet unzips the file and saves them on local system for future use.
2. **01_basic_summaries.py:** Python script performing univariate and bivariate analysis. Creates summary files that are further used in Streamlit application.
3. **02_benchmarking.ipynb:** Python notebook performing benchmarking analysis. The notebook has the answers to questions posed in the assessment within itself.
4. **03_streamlit_app.py** Streamlit appliation code, giving flexibility to the user to access the analysis on local system.

__How to run:__

1. Python scripts can be run via Anaconda Prompt or within a Python virtual environment. Run pip install -r requirements.txt within a new environment to install required packages.
2. Python notebook can be accessed via any IDE like VSCode, IntelliJ Idea, Jupyter Notebook, etc.
3. For streamlit app, run within a python environment using "streamlit run 03_streamlit_app.py". The app would open in a web browser.
