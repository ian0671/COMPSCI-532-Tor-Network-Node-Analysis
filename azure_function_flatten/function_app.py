import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp()


@app.blob_trigger(arg_name="myblob", path="abuseipdb/{name}",
                               connection="DefaultEndpointsProtocol=https;AccountName=compsci532mlwo6133466000;AccountKey=9WpasXAzf4kL32KOwOJQmQj2Ns8sDxljJPs0jSwASCmUVyz4HSVMRQnu7Xxcbr9+oHkU9xmDOICX+AStSyqETg==;EndpointSuffix=core.windows.net") 
def flatten_blob_trigger(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")


# This example uses SDK types to directly access the underlying BlobClient object provided by the Blob storage trigger.
# To use, uncomment the section below and add azurefunctions-extensions-bindings-blob to your requirements.txt file
# Ref: aka.ms/functions-sdk-blob-python
#
# import azurefunctions.extensions.bindings.blob as blob
# @app.blob_trigger(arg_name="client", path="abuseipdb/{name}",
#                   connection="DefaultEndpointsProtocol=https;AccountName=compsci532mlwo6133466000;AccountKey=9WpasXAzf4kL32KOwOJQmQj2Ns8sDxljJPs0jSwASCmUVyz4HSVMRQnu7Xxcbr9+oHkU9xmDOICX+AStSyqETg==;EndpointSuffix=core.windows.net")
# def flatten_blob_trigger(client: blob.BlobClient):
#     logging.info(
#         f"Python blob trigger function processed blob \n"
#         f"Properties: {client.get_blob_properties()}\n"
#         f"Blob content head: {client.download_blob().read(size=1)}"
#     )



@app.blob_trigger(arg_name="myblob", path="censys/{name}",
                               connection="DefaultEndpointsProtocol=https;AccountName=compsci532mlwo6133466000;AccountKey=9WpasXAzf4kL32KOwOJQmQj2Ns8sDxljJPs0jSwASCmUVyz4HSVMRQnu7Xxcbr9+oHkU9xmDOICX+AStSyqETg==;EndpointSuffix=core.windows.net") 
def flatten_blob_trigger_censys(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")


# This example uses SDK types to directly access the underlying BlobClient object provided by the Blob storage trigger.
# To use, uncomment the section below and add azurefunctions-extensions-bindings-blob to your requirements.txt file
# Ref: aka.ms/functions-sdk-blob-python
#
# import azurefunctions.extensions.bindings.blob as blob
# @app.blob_trigger(arg_name="client", path="censys/{name}",
#                   connection="DefaultEndpointsProtocol=https;AccountName=compsci532mlwo6133466000;AccountKey=9WpasXAzf4kL32KOwOJQmQj2Ns8sDxljJPs0jSwASCmUVyz4HSVMRQnu7Xxcbr9+oHkU9xmDOICX+AStSyqETg==;EndpointSuffix=core.windows.net")
# def flatten_blob_trigger_censys(client: blob.BlobClient):
#     logging.info(
#         f"Python blob trigger function processed blob \n"
#         f"Properties: {client.get_blob_properties()}\n"
#         f"Blob content head: {client.download_blob().read(size=1)}"
#     )
