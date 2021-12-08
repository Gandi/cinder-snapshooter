# Cinder-snapshooter
This is a collection of scripts to allow automatic snapshot creation on Openstack Cinder Volumes

## Usage
This project comes with one command `cinder-snapshooter` with the following subcommands:
 
 * `creator`: Creates automatic snapshots on volumes needing one
 * `destroyer`: Destroys expired snapshots
 
Both commands have a `dry-run` and `all-projects` flag to control the behavior, refer
to the commands `--help` for more details.

To enroll a volume to automatic snapshot creation it must have the `automatic_snapshots` property set to `true`,
you can do so using the following openstack command:
```commandline
openstack volume set --property automatic_snapshots=true "<volume_id>"
```

### Run automatically using systemd timers
You can use a set of two systemd timers+service to handle the creation and deletion of snapshots, here is an example
of such units for `cinder-snapshooter creator`.

```unit file (systemd)
;cinder-snapshooter-creator.timer
[Unit]
Description=Run cinder-snapshooter creator daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

```unit file (systemd)
;cinder-snapshooter-creator.service
[Unit]
Description=Creates automated snapshots

[Service]
Type=oneshot
; Here are my environment variable for configuration
EnvironmentFile=/etc/default/cinder-snapshooter
ExecStart=/path/to/venv/bin/cinder-snapshooter creator
; I put my clouds.yml file in this directory
WorkingDirectory=/var/lib/cinder-snapshooter
User=cinder-snapshooter
```

### Environment variables for configuration

Some configuration options are available using environment variables for ease of use:

 * OS_CLOUD: Name of the cloud to use in your clouds.yml file
 * ALL_PROJECTS: Whether to work on all projects or not (requires a user with the appropriate rights, usually admin)
 

## Run tests

```commandline
poetry run pytest
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate and to write meaningful commit messages.

## Licence
[Apache 2.0](https://choosealicense.com/licenses/apache-2.0/)

Copyright 2021 Gandi SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.