# [START documentation]
# set up connectivity from airflow to gcp using [key] in json format
# create new bucket - cayena-bucket [GoogleCloudStorageCreateBucketOperator]
# run web scrapping script [PythonOperator]
# list objecs on the cayena bucket [GCSListObjectsOperator]
# delete local data files [PythonOperator]
# create datatset on bigquery [BigQueryCreateEmptyDatasetOperator]
# transfer file in gcs to bigquery [GCSToBigQueryOperator]
# verify count of rows (if not null) [BigQueryCheckOperator]
# [END documentation]

# [START import module]
from airflow import DAG
from datetime import datetime
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.contrib.operators.gcs_operator import GoogleCloudStorageCreateBucketOperator
from airflow.providers.google.cloud.operators.gcs import GCSListObjectsOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateEmptyDatasetOperator, BigQueryCheckOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.operators.dummy import DummyOperator
from cayena_etl.src.domain.main import etl_web_scrapping
# [END import module]

# [START import variables]
PROJECT_ID = Variable.get("cayena_project_id")
CAYENA_BUCKET = Variable.get("cayena_bucket")
BUCKET_LOCATION = Variable.get("cayena_bucket_location")
BQ_DATASET_NAME = Variable.get("cayena_bq_dataset_name")
BQ_TABLE_NAME = Variable.get("cayena_bq_table_name")
# [END import variables]

# [START default args]
default_args = {
    'owner': 'Felipe Gomes',
    'depends_on_past': False
}
# [END default args]

# [START instantiate dag]
with DAG(
    dag_id="gcp-gcs-bigquery-cayena",
    tags=['development', 'cloud storage', 'google bigquery', 'cayena'],
    default_args=default_args,
    start_date=datetime(year=2022, month=5, day=5),
    schedule_interval='@daily',
    catchup=False,
    description="ETL Process for Cayena Case"
) as dag:
# [END instantiate dag]

# [START set tasks]

    # create start task
    start = DummyOperator(task_id="start")
    
    # create end task
    end = DummyOperator(task_id="end")
    
    # create gcp bucket to cayena - cayena-bucket
    # https://airflow.apache.org/docs/apache-airflow-providers-google/stable/_modules/airflow/providers/google/cloud/operators/gcs.html
    create_gcs_cayena_bucket = GoogleCloudStorageCreateBucketOperator(
        task_id="create_gcs_cayena_bucket",
        bucket_name=CAYENA_BUCKET,
        storage_class='STANDARD',
        location=BUCKET_LOCATION,
        labels={'env': 'dev', 'team': 'airflow'},
        gcp_conn_id="gcp_cayena"
    )
    
    # web scrapping scrit for site - https://books.toscrape.com/catalogue/page-1.html
    # https://airflow.apache.org/docs/apache-airflow/stable/_api/airflow/operators/python/index.html#airflow.operators.python.PythonOperator
    run_web_scrapping_script = PythonOperator(
        task_id='run_web_scrapping_script',
        python_callable=etl_web_scrapping,
        provide_context=True,
        op_kwargs={
            "ingestion_date":"{{ ds }}",
            "bucket_name":CAYENA_BUCKET
        }
    )
    
    # list files inside of gcs bucket - books-daily-data from cayena bucket
    # https://registry.astronomer.io/providers/google/modules/gcslistobjectsoperator
    list_files_from_cayena_bucket_books_daily_data = GCSListObjectsOperator(
        task_id="list_files_from_cayena_bucket_books_daily_data",
        bucket=CAYENA_BUCKET,
        prefix="books-daily-data/",
        gcp_conn_id="gcp_cayena"
    )
    
    # create dataset for google bigquery engine
    # https://registry.astronomer.io/providers/google/modules/bigquerycreateemptydatasetoperator
    bq_create_dataset_cayena = BigQueryCreateEmptyDatasetOperator(
        task_id="bq_create_dataset_cayena",
        dataset_id=BQ_DATASET_NAME,
        gcp_conn_id="gcp_cayena"
    )
    
    # ingest data into bigquery engine
    # https://registry.astronomer.io/providers/google/modules/gcstobigqueryoperator
    ingest_books_into_table_cayene = GCSToBigQueryOperator(
        task_id="ingest_books_into_table_cayene",
        bucket=CAYENA_BUCKET,
        source_objects=['books-daily-data/*.csv'],
        destination_project_dataset_table=f"{PROJECT_ID}.{BQ_DATASET_NAME}.{BQ_TABLE_NAME}",
        source_format='csv',
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
        skip_leading_rows=1,
        time_partitioning = {"field":"ingestion_date","type":"DAY"},
        gcp_conn_id="gcp_cayena",
    )
    
    # check rows inside bigquery table
    # https://registry.astronomer.io/providers/google/modules/bigquerycheckoperator
    check_bq_cayena_table_count = BigQueryCheckOperator(
        task_id="check_bq_cayena_table_count",
        sql=f"SELECT COUNT(*) FROM {BQ_DATASET_NAME}.{BQ_TABLE_NAME}",
        use_legacy_sql=False,
        location="US",
        gcp_conn_id="gcp_cayena"
    )
# [END set tasks]

# [START task sequence]
start >> create_gcs_cayena_bucket >> run_web_scrapping_script >> list_files_from_cayena_bucket_books_daily_data >> bq_create_dataset_cayena >> ingest_books_into_table_cayene >> check_bq_cayena_table_count >> end
# [END task sequence]
