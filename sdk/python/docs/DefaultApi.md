# opsmatesdk.DefaultApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**health_api_v1_health_get**](DefaultApi.md#health_api_v1_health_get) | **GET** /api/v1/health | Health
[**models_api_v1_models_get**](DefaultApi.md#models_api_v1_models_get) | **GET** /api/v1/models | Models

# **health_api_v1_health_get**
> Health health_api_v1_health_get()

Health

### Example
```python
from __future__ import print_function
import time
import opsmatesdk
from opsmatesdk.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = opsmatesdk.DefaultApi()

try:
    # Health
    api_response = api_instance.health_api_v1_health_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->health_api_v1_health_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**Health**](Health.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **models_api_v1_models_get**
> object models_api_v1_models_get()

Models

### Example
```python
from __future__ import print_function
import time
import opsmatesdk
from opsmatesdk.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = opsmatesdk.DefaultApi()

try:
    # Models
    api_response = api_instance.models_api_v1_models_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->models_api_v1_models_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

