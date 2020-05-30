#!/bin/bash
for I in {1..10} 
do
    ./neteye_process_check_result host host_template service service_template plugin_output 1 ./test.log  &
done