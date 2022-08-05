#!/usr/bin/env python
# coding: utf-8

# ### OCI Data Science - Useful Tips
# <details>
# <summary><font size="2">Check for Public Internet Access</font></summary>
# 
# ```python
# import requests
# response = requests.get("https://oracle.com")
# assert response.status_code==200, "Internet connection failed"
# ```
# </details>
# <details>
# <summary><font size="2">Helpful Documentation </font></summary>
# <ul><li><a href="https://docs.cloud.oracle.com/en-us/iaas/data-science/using/data-science.htm">Data Science Service Documentation</a></li>
# <li><a href="https://docs.cloud.oracle.com/iaas/tools/ads-sdk/latest/index.html">ADS documentation</a></li>
# </ul>
# </details>
# <details>
# <summary><font size="2">Typical Cell Imports and Settings for ADS</font></summary>
# 
# ```python
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline
# 
# import warnings
# warnings.filterwarnings('ignore')
# 
# import logging
# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.ERROR)
# 
# import ads
# from ads.dataset.factory import DatasetFactory
# from ads.automl.provider import OracleAutoMLProvider
# from ads.automl.driver import AutoML
# from ads.evaluations.evaluator import ADSEvaluator
# from ads.common.data import ADSData
# from ads.explanations.explainer import ADSExplainer
# from ads.explanations.mlx_global_explainer import MLXGlobalExplainer
# from ads.explanations.mlx_local_explainer import MLXLocalExplainer
# from ads.catalog.model import ModelCatalog
# from ads.common.model_artifact import ModelArtifact
# ```
# </details>
# <details>
# <summary><font size="2">Useful Environment Variables</font></summary>
# 
# ```python
# import os
# print(os.environ["NB_SESSION_COMPARTMENT_OCID"])
# print(os.environ["PROJECT_OCID"])
# print(os.environ["USER_OCID"])
# print(os.environ["TENANCY_OCID"])
# print(os.environ["NB_REGION"])
# ```
# </details>

# In[9]:


import pandas as pd
import oci
import time
import os
from os.path import exists
from sklearn.metrics import get_scorer
from ads.automl.provider import OracleAutoMLProvider
from ads.automl.driver import AutoML
from ads.dataset.factory import DatasetFactory
## USE ADS for model building
import ads
import logging
import seaborn as sns
from ads.evaluations.evaluator import ADSEvaluator
from ads.model.framework.automl_model import AutoMLModel
from oci.object_storage import ObjectStorageClient
from datetime import date
from ads.model.deployment import ModelDeployer, ModelDeploymentProperties
from ads.common.model import ADSModel


# In[5]:


project_id = "ocid1.datascienceproject.oc1.iad.amaaaaaawe6j4fqaw3ecmjlltiwitw26azxbthwqpr4cyda32apaa3xiduea"
compartment_id = "ocid1.compartment.oc1..aaaaaaaacutdz6tyvxv5ujhq62ag3bbryocnpyty6mndu2sseba3cynnpxlq"

retrieve_files_loc = os.getcwd()
rec_filename = "Wallet_DataSoftLogicADW.zip"


# In[10]:


def main():
    ads.set_auth(auth='resource_principal')
    df_readmission_report_v= get_data()
    data = get_ads_df(df_readmission_report_v)
    model_artifact= run_model(data)
    mc_model_id=modelCatalog_entry(model_artifact)
    upload_results_ADW(mc_model_id)

def get_data():
    conn_os = {
    "bucket_name": "readmission_training",
    "file_name": "Train_data_2.csv",
    "namespace": "orasenatdpltintegration03"
    }
    rps = oci.auth.signers.get_resource_principals_signer()
    oci_client = ObjectStorageClient({}, signer=rps)
    df_readmission_report_v = pd.read_csv(f"oci://{conn_os['bucket_name']}@{conn_os['namespace']}/{conn_os['file_name']}", storage_options={"config": {}})
    print(f"Original training dataset: {df_readmission_report_v.head()}")
    return df_readmission_report_v

def get_ads_df(df_readmission_report_v):
    df_readmission_report_v.to_csv(path_or_buf="READMISSION_REPORT_V.csv", index=False)
    age_df = df_readmission_report_v[['PATIENT_NUM','AGE','GENDER_NAME']].drop_duplicates()
    tmp = df_readmission_report_v.groupby(['PATIENT_NUM','OBSERVATION_CODE']).agg({'OBSV_VALUE_NUMERIC': ['min','max', 'mean','std']})
    tmp1 = tmp.reset_index()
    tmp1.columns=['PATIENT_NUM','OBSERVATION_CODE','OBS_MIN','OBS_MAX','OBS_MEAN','OBS_std']
    # Pivot to get one row for each patient
    tmp2=pd.pivot_table(tmp1,columns=['OBSERVATION_CODE'],index=['PATIENT_NUM'],values=['OBS_MIN','OBS_MAX','OBS_MEAN','OBS_std'])

    tmp2.columns = [col[0]+"_"+col[1] for col in tmp2.columns]
    tmp3 = tmp2.reset_index()
    tmp4= tmp3[[col for col in tmp3.columns if not 'READ' in col]]
    target_df=df_readmission_report_v[['PATIENT_NUM','READMISSION_FLG']].drop_duplicates()
    final_df1 = target_df.merge(age_df, how='inner', on='PATIENT_NUM')
    final_df2 = final_df1.merge(tmp4, how='inner',on = 'PATIENT_NUM')
    final_df3 = final_df2.fillna(0)
    final_df4 = final_df3.drop(columns=['PATIENT_NUM'])
    ds = DatasetFactory.from_dataframe(final_df4,target="READMISSION_FLG")
    print(f"Training dataset after processing for model training: {ds.head()}")
    return ds

def run_model(data):
#    os.environ['GIT_PYTHON_REFRESH']="quiet"
    ml_engine = OracleAutoMLProvider()
    train, test = data.train_test_split(test_size=0.2)
    oracle_automl = AutoML(train, provider=ml_engine)
    automl_model1, baseline1 = oracle_automl.train() # alglrithm selection is done here
    #create model_artifact
    model = ADSModel.from_estimator(automl_model1)
    model_artifact_path = f"/home/datascience/Automl_artifacts_{get_timestamp()}"
    my_published_conda = '/conda_environments/cpu/generalml_p37_cpu_custom/1.0/generalml_p37_cpu_customv1_0'
    model_artifact = model.prepare(model_artifact_path, inference_conda_env=my_published_conda, force_overwrite=True, data_sample=train, fn_artifact_files_included=False)
    return model_artifact


def modelCatalog_entry(model_artifact):
    display_name = f"Patient Readmission Model {get_timestamp()}"
    description = "Predicts whether patient will be readmitted based on historical data"
    ignore_pending_changes = True
    mc_model=model_artifact.save(project_id=project_id, compartment_id=compartment_id, display_name=display_name,
    description=description, ignore_pending_changes=ignore_pending_changes)
    return mc_model.id

def download_wallet():
    rps = oci.auth.signers.get_resource_principals_signer()
    mybucketname = "readmission_scripts"
    
    prefix_files_name = "wallets/Wallet_DataSoftLogicADW.zip"
    object_storage = oci.object_storage.ObjectStorageClient(config={}, signer=rps)
    namespace = object_storage.get_namespace().data
    listfiles = object_storage.list_objects(namespace,mybucketname,prefix=prefix_files_name)
    for filenames in listfiles.data.objects:
        get_obj = object_storage.get_object(namespace, mybucketname,filenames.name)
        with open(retrieve_files_loc+'/'+rec_filename,'wb') as f:
            for chunk in get_obj.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)
                
def get_timestamp():
    today = datetime.today()
    tzname = time.tzname[time.daylight]
    mmdd = today.strftime(f"%m%d_%H:%M:%S_{tzname}")
    return mmdd

def upload_results_ADW(mc_model_id):
    # Gives the below error due to very long model_id
    #cx_Oracle.DatabaseError: ORA-00910: specified length too long for its datatype
    conn = {
        "user_name": "ADMIN",
        "password": "Welcome!2345",
        "service_name": "datasoftlogicadw_high", 
        # the service levels can be found in <ADW wallet folder>/tnsnames.ora as one of the variable names to which the connection string value is assigned
        "wallet_location": retrieve_files_loc+'/'+rec_filename
        }
    print("mc_model_id", mc_model_id)
    download_wallet()
    series = pd.Series(["Readmission",mc_model_id], index=['MODEL_NAME','LATEST_MODEL_ID'])
    df = pd.DataFrame([series])
    ds = DatasetFactory.from_dataframe(df)
    
    
    ds.ads.to_sql("ADMIN.MODELS_INFO", connection_parameters=conn, if_exists='replace')
    print("done uploading to ADW")
    

if __name__ == '__main__':
    main()


# In[ ]:




