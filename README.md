[![CI](https://github.com/diconico07/cinder-snapshooter/actions/workflows/CI.yml/badge.svg?event=push)](https://github.com/diconico07/cinder-snapshooter/actions/workflows/CI.yml)
# Cinder-snapshooter
This is a collection of scripts to allow automatic snapshot creation on Openstack Cinder Volumes

## Snapshots policy
If you run the creator script at least every day, it shall create a snapshot per day for every volume with automatic
snapshots enabled.

These snapshots will expire after 7 days, except for the first snapshot of the month that will expire after 3 months.

This let you with a maximum of 11 automatic snapshots for any given volume (4 "monthly" and 7 "daily"). Let see it with
an example:

I activate automatic snapshots on a volume on 15 January. On 8 April I will have the following snapshots:
 - 15 January, expire on 15 April
 - 1st February, expire on 1st May
 - 1st March, expire on 1st June
 - 1st April, expire on 1st July
 - 2 April, expire on 9 April
 - 3 April, expire on 10 April
 - 4 April, expire on 11 April
 - 5 April, expire on 12 April
 - 6 April, expire on 13 April
 - 7 April, expire on 14 April
 - 8 April, expire on 15 April

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

### Use the docker image
This project comes with a `Dockerfile` to generate a docker image. 

You can use it this way (here with snapshot creator):
```sh
docker run --mount type=bind,src=$HOME/.config/openstack,dst=/root/.config/openstack -e OS_CLOUD=gandi ghcr.io/diconico07/cinder-snapshooter:latest creator
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