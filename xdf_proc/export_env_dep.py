import subprocess
import sys

def get_conda_dependencies():
    # Get conda dependencies
    conda_list = subprocess.check_output(['conda', 'list', '--explicit']).decode('utf-8')
    return conda_list.split('\n')[2:-1]  # Skipping header and empty last line

def get_pip_dependencies():
    # Get pip dependencies
    pip_freeze = subprocess.check_output(['pip', 'freeze']).decode('utf-8')
    return pip_freeze.split('\n')

def save_conda_dependencies_to_file(conda_dependencies, output_file='environment.yml'):
    # Save conda dependencies to a YAML file
    with open(output_file, 'w') as f:
        f.write('channels:\n')
        f.write('  - defaults\n')  # Default channel
        for dependency in conda_dependencies:
            f.write('  - ' + dependency + '\n')
        f.write('dependencies:\n')
        f.write('  - python=' + sys.version.split()[0] + '\n')  # Add Python version

def save_pip_dependencies_to_file(pip_dependencies, output_file='requirements.txt'):
    # Save pip dependencies to a requirements.txt file
    with open(output_file, 'w') as f:
        for dependency in pip_dependencies:
            f.write(dependency + '\n')

def main():
    # Get dependencies
    conda_dependencies = get_conda_dependencies()
    pip_dependencies = get_pip_dependencies()

    # Save to files
    save_conda_dependencies_to_file(conda_dependencies)
    save_pip_dependencies_to_file(pip_dependencies)

    print("Conda dependencies saved to environment.yml")
    print("Pip dependencies saved to requirements.txt")

if __name__ == "__main__":
    main()
