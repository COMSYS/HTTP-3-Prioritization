# HTTP/3 Prioritization Testbed

This repository contains the testbed implementation of our HTTP/3 Prioritization Testbed.

## Publication

* Constantin Sander, Ike Kunze and Klaus Wehrle: *Analyzing the Influence of Resource Prioritization on HTTP/3 HOL Blocking and Performance*. In Proceedings of the Network Traffic Measurement and Analysis Conference (TMA '22), 2022.

If you use any portion of our work, please consider citing our publication.

```
@inproceedings {2022-sander-h3-prio-hol,
   title = {{Analyzing the Influence of Resource Prioritization on HTTP/3 HOL Blocking and Performance}},
   year = {2022},
   month = {6},
   day = {19},
   booktitle = {Proceedings of the Network Traffic Measurement and Analysis Conference (TMA '22)},
   DOI = {},
   author = {Sander, Constantin and Kunze, Ike and Wehrle, Klaus}
}
```

## Content

### Adapted H2O Webserver

The ```h20``` subrepo contains our adapted h2o webserver which prioritizes resources according to a prioritization hint file.
To enable the custom prioritization use ```h2o -p <prio_mode> -P <prio_hint>```, where prio_mode is one of firefoxtree, firefoxext, rrtree, wrrtree, chrometree and prio_hint is the prioritization hint file.
The prio hint file has the form ```<uri>#<resource_type>#<chrome_prio_class>#<firefox_prio_class>#<firefox_prio_weight>```. It can be created using the ```get_prios.py``` script as described below.

### Adapted Chromium / Browsertime Docker Container

```browsertime/docker``` contains our adapted chromium / browsertime docker container. Please compile chromium 95.0.4638.54 in the chromium subdirectory with the ```chromium_patch``` applied to enable disabling the fetch credentials.
Afterwards, you can create the image using ```./build.sh```.

### Orchestration / Testbed Software

```main.py``` is the main script to start the testbed, instantiating the namespaces and running the tests.
Please run the script using python3 and with sudo rights to enable creating namespaces.
Before, please create the docker image, compile and install h2o and build our fastcgi backend in ```go_fastcgi``` using the build script.

#### H2 Prioritization Retrieval
 To retrieve the prioritization information, you can run ```python3 main.py <namespacename> --workdir <mahimahifiles> --website <www.website.com> --h2prioout <intermediatepriofile>``` to retrieve h2o logfiles and chromium logfiles.
 The file can then be processed by ```python3 get_prios.py --workdir <mahimahifiles> --input <intermediatepriofile> --output <priohintfile>```.

#### H3 Evaluation
For the actual evaluation, you can run ```python3 main.py <namespacename> --eval evalconfig.json```.
evalconfig.json contains the eval configs, where the first line describes general settings like output directory and repeat count. The following lines describes parameters settings for bandwidth, rtt, website recording, etc.

### Evaluation
The ```eval``` directory contains our aggregation and HOL evaluation script to process the testbed output and to extract the metrics.
Running ```python3 aggregate.py <outputdir>``` allows to aggregate all data including our HOL metric.

### Dataset
 The ```processed_data``` directory contains our results including webperformance metrics and HOL per run.