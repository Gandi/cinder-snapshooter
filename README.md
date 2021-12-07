# Cinder-snapshooter
This is a collection of scripts to allow automatic snapshot creation on Openstack Cinder Volumes

## Usage
This project comes with two scripts `cinder-snapshooter-creator` and `cinder-snapshooter-destroyer` that creates
automatic snapshots and destroys expired snapshots.

To enroll a volume to automatic snapshot creation it must have the `automatic_snapshots` property set to `true`,
you can do so using the following openstack command:
```commandline
openstack volume set --property automatic_snapshots=true "<volume_id>"
```

### Run automatically using systemd timers
You can use a set of two systemd timers+service to handle the creation and deletion of snapshots, here is an example
of such units for `cinder-snapshooter-creator`.

```unit file (systemd)
;cinder-snapshooter-creator.timer
[Unit]
Description=Run cinder-snapshooter-creator daily

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
ExecStart=/path/to/venv/bin/cinder-snapshooter-creator
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