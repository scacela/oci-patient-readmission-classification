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

# In[14]:


import pandas as pd
import oci
import time
from datetime import datetime
import os
from os.path import exists
import ads
from ads.dataset.factory import DatasetFactory
import logging
from ads.model.deployment import ModelDeployer, ModelDeploymentProperties
from ads.catalog.model import ModelCatalog
import tempfile


# In[5]:


project_id = "ocid1.datascienceproject.oc1.iad.amaaaaaawe6j4fqaw3ecmjlltiwitw26azxbthwqpr4cyda32apaa3xiduea"
compartment_id = "ocid1.compartment.oc1..aaaaaaaacutdz6tyvxv5ujhq62ag3bbryocnpyty6mndu2sseba3cynnpxlq"
model_name="Readmission"

retrieve_files_loc = os.getcwd()
rec_filename = "Wallet_DataSoftLogicADW.zip"


# In[7]:


def main():
    ads.set_auth(auth='resource_principal')
    download_wallet()
    mc_model_id=modelCatalog_entry(model_name)
    deployment = deploy(mc_model_id)
    print("done with deployment")
    inference_data = get_inference_data()
    data = get_ads_df(inference_data)
    # results = mc_predict(mc_model_id, inference_data)
    results = predict(deployment, data)
    upload_results_ADW(results)
    clean_up(deployment)
    
def clean_up(deployment):
    deployment.delete(wait_for_completion=True)

def modelCatalog_entry(model_name):
    conn = {
        "user_name": "ADMIN",
        "password": "Welcome!2345",
        "service_name": "datasoftlogicadw_high", 
        # the service levels can be found in <ADW wallet folder>/tnsnames.ora as one of the variable names to which the connection string value is assigned
        "wallet_location": "Wallet_DataSoftLogicADW.zip"
    }
    
    df = pd.DataFrame.ads.read_sql(
    """SELECT * FROM ADMIN.MODELS_INFO """,
    connection_parameters=conn,
    )
    mc_model_id= df[df["MODEL_NAME"]==model_name]['LATEST_MODEL_ID'][0]
    print("model id", mc_model_id)
    return mc_model_id
   
def get_inference_data():
    conn_os = {
        "bucket_name": "readmission_inference",
        "namespace": "orasenatdpltintegration03",
        "file_name": "Infer_data_2.csv"
    }
    
    ds = pd.read_csv(f"oci://{conn_os['bucket_name']}@{conn_os['namespace']}/{conn_os['file_name']}", storage_options={"config": {}})
    
    
    pd.set_option('display.max_columns', 200)
    pd.set_option('display.max_rows', 200)
    #df_inference = df.drop(['ID'], axis=1, errors='ignore')
    # inference_data=ds.to_json()

    # return inference_data
    return ds

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
    ds = final_df3.drop(columns=['PATIENT_NUM'])
    
    inference_data_json = ds.to_json()
    return inference_data_json

def download_wallet():
    rps = oci.auth.signers.get_resource_principals_signer()
    mybucketname = "readmission_scripts"
    retrieve_files_loc = os.getcwd()
    prefix_files_name = "wallets/Wallet_DataSoftLogicADW.zip"
    object_storage = oci.object_storage.ObjectStorageClient(config={}, signer=rps)
    namespace = object_storage.get_namespace().data
    listfiles = object_storage.list_objects(namespace,mybucketname,prefix=prefix_files_name)
    for filenames in listfiles.data.objects:
        get_obj = object_storage.get_object(namespace, mybucketname,filenames.name)
        with open(retrieve_files_loc+'/'+rec_filename,'wb') as f:
            for chunk in get_obj.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)
    
def upload_results_ADW(results):
    conn = {
        "user_name": "ADMIN",
        "password": "Welcome!2345",
        "service_name": "datasoftlogicadw_high", 
        # the service levels can be found in <ADW wallet folder>/tnsnames.ora as one of the variable names to which the connection string value is assigned
        "wallet_location": retrieve_files_loc+'/'+rec_filename
    }
    print("print results before conversion", results)
    df = pd.DataFrame(results)
    ds = DatasetFactory.from_dataframe(df)
    print("print results after", ds )
    
    ds.ads.to_sql("ADMIN.READMISSION_ANALYSIS", connection_parameters=conn, if_exists='replace')
    print("done uploading to ADW")

def get_timestamp():
    today = datetime.today()
    tzname = time.tzname[time.daylight]
    mmdd = today.strftime(f"%m%d_%H:%M:%S_{tzname}")
    return mmdd

def deploy(mc_model_id):
    deployer = ModelDeployer(config={})
    print("inside deployment")
    deployment_properties = ModelDeploymentProperties(mc_model_id
            ).with_prop('display_name', f"Patient Readmission MD {get_timestamp()}"
            ).with_prop("project_id", project_id
            ).with_prop("compartment_id", compartment_id
            ).with_instance_configuration(
                    config={"INSTANCE_SHAPE":"VM.Standard2.1",
                            "INSTANCE_COUNT":"1",
                            'bandwidth_mbps':10}
            ).with_access_log(log_group_id="ocid1.loggroup.oc1.iad.amaaaaaawe6j4fqagf3pv32obdkhdk7mn5owvqqqeoebhg5spd4oril7cxsq", log_id="ocid1.log.oc1.iad.amaaaaaawe6j4fqa4adeilezl54la6xwzwbyga2py6vlapxgu3lekonqpyiq"
            ).with_predict_log(log_group_id="ocid1.loggroup.oc1.iad.amaaaaaawe6j4fqagf3pv32obdkhdk7mn5owvqqqeoebhg5spd4oril7cxsq", log_id="ocid1.log.oc1.iad.amaaaaaawe6j4fqaskyvovdv2ugn3lzzftnmyq7dsv2x25qggntw6yyx5cgq"
            ).build()
    deployment = deployer.deploy(deployment_properties,
            max_wait_time=1000, poll_interval=15)
    print("almost done with deployment")
    return deployment

def predict(deployment, inference_data):
    print("Print")
    prediction = deployment.predict(inference_data)
    # Relate the prediction results to respective patient_num and upload the results for each patient
    return prediction

# def mc_predict(mc_model_id, inference_data):
#     mc_model_id="ocid1.datasciencemodel.oc1.iad.amaaaaaad4alhfiadezvnysl6njqekioeixmqmyhtqhojccq2aokzck6ocvq"
#     mc = ModelCatalog(compartment_id=compartment_id)
#     download_path = tempfile.mkdtemp()
#     dl_model_artifact = mc.download_model(mc_model_id, download_path, force_overwrite=True)
#     dl_model_artifact.reload(model_file_name='model.pkl')
#     inference_df = pd.read_json(inference_data, orient ='index')
#     prediction = dl_model_artifact.model.predict(inference_df)
#     return prediction

if __name__ == '__main__':
    main()


# ## To Be Continued:
# 
# Investigage Model Deployment failure. Saw this error:
# ```
#     "exception :: Failed to initialize: Bad git executable.\nThe git executable must be specified in one of the following ways:\n    - be included in your $PATH\n    - be set via $GIT_PYTHON_GIT_EXECUTABLE\n    - explicitly set via git.refresh()\n\nAll git commands will error until this is rectified.\n\nThis initial warning can be silenced or aggravated in the future by setting the\n$GIT_PYTHON_REFRESH environment variable. Use one of the following values:\n    - quiet|q|silence|s|none|n|0: for no warning or exception\n    - warn|w|warning|1: for a printed warning\n    - error|e|raise|r|2: for a raised exception\n\nExample:\n    export GIT_PYTHON_REFRESH=quiet\n"
# ```
# Alternatively, you can load the Model Catalog entry onto this machine. That would be best because it would spare the user of having to wait for Model Deployment infrastructure to provision for each inference operation.

# In[ ]:




