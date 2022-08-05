
### Steps to create custom conda env:

1. Install default conda env:
```
odsc conda install -s generalml_p37_cpu_v1
```
### ISSUE 1:
After initial install, Train.py fails with the first error:
```
from ads.model.framework.automl_model import AutoMLModel
ModuleNotFoundError: No module named 'ads.model.framework'
```
Solution: Default version installed is 2.5.4, we are forced to use 2.5.10\
Resolution:
1. Cloned the conda env into custom conda env:
```
odsc conda clone -f /home/datascience/conda/generalml_p37_cpu_v1 -e generalml_p37_cpu_custom
```
2. Install latest ads on the new custom conda env:
```
conda activate /home/datascience/conda/generalml_p37_cpu_customv1_0
pip install oracle-ads==2.5.10
```
This results in the following error:
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
tensorflow 2.6.2 requires numpy~=1.19.2, but you have numpy 1.21.6 which is incompatible.
tensorflow 2.6.2 requires typing-extensions~=3.7.4, but you have typing-extensions 4.0.1 which is incompatible.
oci-cli 3.4.3 requires oci==2.54.1, but you have oci 2.75.1 which is incompatible.
```
### ISSUE 2

Running Train.py next leads to the following error:
```
from onnxconverter_common.auto_mixed_precision import *  # noqa
ModuleNotFoundError: No module named 'onnxconverter_common.auto_mixed_precision'
```
Resolution:
```
pip install onnxconverter-common==1.9.0
```
### Publish the custom conda env to Object storage:
```
odsc conda init -b hc-lakehouse-custom-conda-envs -n oraclehealthcaredev -a resource_principal
```
```
odsc conda publish -s generalml_p37_cpu_customv1_0
```
While publishing the env, we see the following error:
```
FileNotFoundError: [Errno 2] No such file or directory: '/home/datascience/conda/generalml_p37_cpu_customv1_0/lib/python3.7/site-packages/skl2onnx-1.9.3.dist-info/INSTALLER'
```
#### Resolution:
Cleaned the libraries:
```
rm /home/datascience/conda/generalml_p37_cpu_customv1_0/conda-meta/skl2onnx-1.9.3*.json
```
Next error:
```
FileNotFoundError: [Errno 2] No such file or directory: '/home/datascience/conda/generalml_p37_cpu_customv1_0/lib/python3.7/site-packages/onnxconverter_common-1.8.1.dist-info/INSTALLER'
```
Resolution:
```
rm /home/datascience/conda/generalml_p37_cpu_customv1_0/conda-meta/onnxconverter-common-1.8.1*.json
```
Next Error:
```
FileNotFoundError: [Errno 2] No such file or directory: '/home/datascience/conda/generalml_p37_cpu_customv1_0/lib/python3.7/site-packages/numpy-1.19.5.dist-info/INSTALLER'
```
Resolution:
```
rm /home/datascience/conda/generalml_p37_cpu_customv1_0/conda-meta/numpy-1.19.5*.json
```
### DONE with publishing