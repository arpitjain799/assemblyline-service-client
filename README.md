# ALv4 Service Client #

This service client fetches tasks from the service server and drops them into a directory. It will then wait for output 
file(s) produced by the v3 or v4 service. This independent service client allows the service to run independently in 
Python3, Python2, Java, C++, etc. A service will monitor a directory for a file with it's associated task.json, will 
process it and drop a result.json file which the service_client can in turn pick up to send back to the service_server.