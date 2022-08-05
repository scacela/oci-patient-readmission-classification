# OCI Patient Readmission Classification

## Business case
A healthcare provider is looking to track which patients are likely to be readmitted based on historical data, so that they can anticipate their patient's needs and provide them the appropriate care.\
\
Patients who have been hospitalized are getting their vitals monitored periodically, and this data is added to a dataset. When each of the patient's vitals have been recorded, the recorded measurements populate a new row in a dataset, along with the patient's age, gender, name, place of residence, diagnosed condition, the date of the onset of the condition, the date of the recorded measurement, and the time since the patient has been discharged from the hospital.\
\
For many patients, their status as patients who have been readmitted to the hospital within 30 days of discharge has been recorded. This is the historical data that the healthcare provider can used to make informed decisions about patients whose status as 30-day-readmitted patients is still to be determined.
## Technical implementation
A number of resources are used to build together a system that can be used to train a machine learning model that can be used to classify patients as likely or unlikely candidates for 30-day-readmission. These resources are listed here.
- [Serve.py](Serve.py): DS Job artifact for using the ML model to perform the inference operation
- [Train.py](Train.py): DS Job artifact for training ML model
- Training data: [Download](https://objectstorage.us-ashburn-1.oraclecloud.com/p/ivMJoamUG_ikAHjFuhB-wYtinA7jzg8eMtuzzl1Vj94DU_XRnR6pSLK13TqS5ci0/n/orasenatdpltintegration03/b/readmission_training/o/Train_data_2.csv)
- Inference data: [Download](https://objectstorage.us-ashburn-1.oraclecloud.com/p/F5oNZzmlLOyvldlenYLYgZ7aXrc4DNzLrMXSgVRJHWFJRhnG7g2WDU6cuuzKF51E/n/orasenatdpltintegration03/b/readmission_inference/o/Infer_data_2.csv) 
- [Architecture_Diagram.pptx](Architecture_Diagram.pptx)
## Additional notes
Additional implementation options to consider for the next version of the architecture diagram:
- For training automation, use OAC as the scheduler instead of Data Integration. From the OAC instance, a Function will be called, which calls the DS Job run.
- Use an events-based approach instead of schedule-based, so that the DS Job Run is triggered by a Function, which is triggered by Events, which responds upon `OBJECT_CREATE` and `OBJECT_UPDATE` events in the training bucket
- Have the training data added as additional rows in an ADW table for training data, rather than as a new or replacement object in the Object Storage Bucket. Have the DS Job triggered upon updates to the ADW table for training data.

Note that Integration Cloud isn't necessarily part of this demo, but rather is a suggestion for integrating with a data source, assuming that the customer uses some non-Oracle data source such as Sharepoint.