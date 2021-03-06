<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [Nature of Metrics](#nature-of-metrics)
- [Naming conventions](#naming-conventions)
  - [Common Naming Conventions](#common-naming-conventions)
    - [Metric Names](#metric-names)
    - [System Dimensions](#system-dimensions)
      - [Common Dimensions](#common-dimensions)
        - [Component Default Dimensions](#component-default-dimensions)
  - [OpenStack Specific Naming Conventions](#openstack-specific-naming-conventions)
    - [Metric Names](#metric-names-1)
    - [OpenStack Dimensions](#openstack-dimensions)
- [Cross-Tenant Metric Submission](#cross-tenant-metric-submission)
- [Statsd](#statsd)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Nature of Metrics

In Monasca, a metric type is uniquely identified by a name and a specific set of dimensions. The set of dimensions of a metric are a dictionary of (key, value) pairs. A measurement is a metric instance with a value and a timestamp. Measurements are searchable from the Monasca API by name and dimension (key, value).

Optionally, a measurement may also contain extra data about the value, which is known as `value_meta`. `value_ meta`[wiki.openstack.org/wiki/Monasca/Value_Metadata](https://wiki.openstack.org/wiki/Monasca/Value_Metadata) are a dictionary of (key, value) pairs that contain textual data that relates to the value of the measurement. If value_meta is included with a measurement, it is returned when the measurement is read via the Monasca API. Unlike dimensions, value_meta is not searchable from the Monasca API, and it is ignored when computing statistics on measurements such as `average`.

# Naming conventions

## Common Naming Conventions

### Metric Names
Although metric names in the Monasca API can be any string the Monasca Agent uses several naming conventions as follows:

* All lowercase characters.
* '.' is used to hierarchially group. This is done for compatibility with Graphite as Graphite assumes a '.' as a delimiter.
* '_' is used to separate words in long names that are not meant to be hierarchical.

### System Dimensions
Dimensions are a dictionary of (key, value) pairs that can be used to describe metrics. Dimensions are supplied to the API by the Agent.

This section documents some of the common naming conventions for dimensions that should observed by the monitoring agents/checks to improve consistency and make it easier to create alarms and perform queries.

The agent will automatically add a hostname dimension, beyond that dimensions are optional. Dimensions can be defined in the primary agent config and
applied to all metrics, set per plugin configuration or set during collection.

The order of precedence for all dimensions is:

&nbsp;&nbsp;1) Any dimension defined in an Agent plugin config file.

&nbsp;&nbsp;2) Any dimension defined in the Agent config file.

&nbsp;&nbsp;3) Any default dimension set in the plugin code itself.

1 being the highest precedence and 3 being the lowest.  If a dimension is defined in more than one place,
 the dimension will be set to the value of the highest precedence above.  This allows dimensions to be overridden at any level if desired.

#### Common Dimensions

| Name | Description |
| ---- | ----------- | 
| hostname | The FQDN of the host being measured. |
| observer_hostname | The FQDN of the host that runs a check against another host. |
| url | In the case of the http endpoint check the url of the http endpoint being checked. |
| device | The device name |
| service | The sevice name that owns this metric |
| component | The component name within the device that the metric comes from |

One way to add additional dimensions for all metrics is by using the `--dimensions` command line option to `monasca-setup`.  This will populate /etc/monasca/agent/agent.yaml with dimensions to be included with all metrics. The syntax is a comma seperated list of name/value pairs, 'name:value,name2:value2'

```
/etc/monasca/agent/agent.yaml

Main:
  dimensions:
    service: monitoring
  hostname: mini-mon
```

##### Component Default Dimensions

| Component Name| Dimensions   |
| -------------- | ------------------------------- |
| Collector | component:monasca-agent |
| Kafka Consumer | component:kafka, service:kafka |
| LibVirt | device:disk[0].device, device:vnic[0].name |
| WMI Check | tag from the result if there's a `tag_by` value (e.g.: "name:jenkins") |
| Zookeeper | component:zookeeper, service:zookeeper |
| Redis | redis_host: localhost, redis_port: port |

## OpenStack Specific Naming Conventions
This section documents some of the naming conventions that are used for monitoring OpenStack.

### Metric Names
Where applicable, each metric name will list the name of the service, such as "compute", component, such as "nova-api", and the check, such as "process_exists". For example, "nova.api.process_exists".

### Dimensions
This section documents the list of dimensions that are commonly used in monitoring OpenStack.

| Name | Description | Examples |
| ---- | ----------- | -------- |
| region | An OpenStack region.  | `uswest` and `useast` |
| zone| An OpenStack zone | Examples include `1`, `2` or `3` |
| service | The name of the OpenStack service being measured. | `compute` or `image` or `monitoring` |
| component | The component in the OpenStack service being measured. |`nova-api`, `nova-scheduler`, `mysql` or `rabbitmq`. |
| resource_id | The resource ID of an OpenStack resource. | |
| tenant_name | The tenant name of the owner of an OpenStack resource. | |

# Cross-Tenant Metric Submission
If the owner of the VM is to receive his or her own metrics, the Agent needs to be able to submit metrics on their behalf.  This is called cross-tenant metric submission.  For this to work, a Keystone role called "monitoring-delegate" needs to be created, and the Agent's Keystone username and project (tenant) assigned to it.  This username is contained as `username` in `/etc/monasca/agent/agent.yaml`, and passed to `monasca-setup` as the `-u` parameter.   The Agent's project name is contained in `agent.yaml` as the variable `project_name`, and passed to `monasca-setup` as the `--project-name` parameter.

In the below example, the Agent's Keystone username is "monasca-agent" and the Agent's Keystone project name is "mini-mon".

Example commands to add the Agent user/project to the monitoring-delegate role:
```
keystone role-create --name=monitoring-delegate

user_id=`keystone user-list |grep monasca-agent |cut -d'|' -f2`
role_id=`keystone role-list |grep monitoring-delegate |cut -d'|' -f2`
tenant_id=`keystone tenant-list |grep mini-mon |cut -d'|' -f2`

keystone user-role-add --user=${user_id// /} --role=${role_id// /} --tenant_id=${tenant_id// /}
```

Once the Agent's user and project are assigned to the `monitoring-delegate` group, the Agent can submit metrics for other tenants.

# Statsd
The Monasca Agent ships with a Statsd daemon implementation called monasca-statsd. A statsd client can be used to send metrics to the Forwarder via the Statsd daemon.

monasca-statsd will accept metrics submitted by functions in either the standard statsd Python client library, or the monasca-agent's [monasca-statsd Python client library](https://github.com/stackforge/monasca-statsd). The advantage of using the python-monasca-statsd library is that it is possible to specify dimensions on submitted metrics. Dimensions are not handled by the standard statsd client.

Statsd metrics are not bundled along with the metrics gathered by the Collector, but are flushed to the agent Forwarder on a separate schedule (every 10 seconds by default, rather than 60 seconds for Collector metrics).

Here is an example of metrics submitted using the standard statsd Python client library.

```
import statsd

statsd.increment('processed', 5)        # Increment 'processed' metric by 5
statsd.timing('pipeline', 2468.34)      # Pipeline took 2468.34 ms to execute
statsd.gauge('gaugething', 3.14159265)  # 'gauge' would be the preferred metric type for Monitoring
```

The [monasca-statsd](https://github.com/stackforge/monasca-statsd library provides a python based implementation of a statsd client but also adds the ability to add dimensions to the the statsd metrics for the client.

Here are some examples of how code can be instrumented using calls to monasca-statsd.
```

    * Import the module once it's installed.
		from monascastatsd import monasca_statsd
		statsd = monasca_statsd.MonascaStatsd()

    * Optionally, configure the host and port if you're running Statsd on a non-standard port.
		statsd.connect('localhost', 8125)

    * Increment a counter.
		statsd.increment('page_views')

		With dimensions:
    	statsd.increment('page_views', 5, dimensions={'Hostname': 'prod.mysql.abccorp.com'})

    * Record a gauge 50% of the time.
		statsd.gauge('users_online', 91, sample_rate=0.5)

		With dimensions:
		statsd.gauge('users_online', 91, dimensions={'Origin': 'Dev', 'Environment': 'Test'})

    * Sample a histogram.
		statsd.histogram('file.upload_size', 20456)

		With dimensions:
		statsd.histogram('file.upload_size', 20456, sample_rate=0.5, dimensions={'Name': 'MyFile.pdf', 'Version': '1.0'})

    * Time a function call.
		@statsd.timed('page.render')
		def render_page():
    	# Render things...

    * Time a block of code.
     with statsd.time('database_read_time',
                      dimensions={'db_host': 'mysql1.mycompany.net'}):
    	# Do something...

```

# License
Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
