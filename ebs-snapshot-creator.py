import boto3
import collections
import datetime

"""
This function snapshots EC2 instances that have a "Backup" tag containing any
value. If there is no "Retention" tag with a value indicating the number of
days, then the default of 7 is given.
"""

session = boto3.session.Session()
region = session.region_name

ec = boto3.client('ec2')


def lambda_handler(event, context):
    reservations = ec.describe_instances(
        Filters=[
            {'Name': 'tag:Backup', 'Values': ['Yes']},
        ]
    ).get(
        'Reservations', []
    )

    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
        ], [])

    print("\tFound %d instances that need backing up" % len(instances))

    to_tag = collections.defaultdict(list)
    instance_cross_region = {}

    for instance in instances:
        try:
            retention_days = [
                int(t.get('Value')) for t in instance['Tags']
                if t['Key'] == 'Retention'][0]
        except IndexError:
            retention_days = 7

        for dev in instance['BlockDeviceMappings']:
            if dev.get('Ebs', None) is None:
                continue

            vol_id = dev['Ebs']['VolumeId']

            dev_name = dev['DeviceName']

            print("\tFound EBS volume %s (%s) on instance %s" % (vol_id, dev_name, instance['InstanceId']))

            # figure out instance name & if cross region backup wanted
            instance_name = ""
            cross_region = ""
            for tag in instance['Tags']:
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                if tag['Key'] == 'BackupCrossRegion':
                    cross_region = tag['Value']

            description = '%s - %s (%s)' % (instance_name, vol_id, dev_name)

            snap = ec.create_snapshot(
                VolumeId=vol_id,
                Description=description
            )

            if (snap):
                print("\tSnapshot %s created in %s of [%s]" % (snap['SnapshotId'], region, description))

            to_tag[retention_days].append(snap['SnapshotId'])

            print(
            "\tRetaining snapshot %s of volume %s from instance %s (%s) for %d days" % (
                snap['SnapshotId'],
                vol_id,
                instance['InstanceId'],
                instance_name,
                retention_days,
            ))

            today_fmt = datetime.date.today().strftime('%Y-%m-%d')
            delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
            delete_fmt = delete_date.strftime('%Y-%m-%d')

            ec.create_tags(
                Resources=[snap['SnapshotId'], ],
                Tags=[
                    {'Key': 'CreatedOn', 'Value': today_fmt},
                    {'Key': 'DeleteOn', 'Value': delete_fmt},
                    {'Key': 'Type', 'Value': 'Automated'},
                ]
            )

            if cross_region:
                ec.create_tags(
                    Resources=[snap['SnapshotId'], ],
                    Tags=[
                        {'Key': 'BackupCrossRegion', 'Value': cross_region}
                    ]
                )