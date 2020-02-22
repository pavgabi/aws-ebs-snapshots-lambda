import boto3
import re
import datetime

""" Searches for snapshots to copy to another region based on the following tags
Type               Automated
CreatedOn          [todays date, e.g. 2018-05-10]
BackupCrossRegion  [single region code or comma separated list, e.g. eu-west-1,eu-west-2]
"""

session = boto3.session.Session()
source_region = session.region_name

ec = boto3.client('ec2')
iam = boto3.client('iam')


def lambda_handler(event, context):
    account_ids = list()
    try:
        """
        You can replace this try/except by filling in `account_ids` yourself.
        Get your account ID with:
        > import boto3
        > iam = boto3.client('iam')
        > print iam.get_user()['User']['Arn'].split(':')[4]
        """
        iam.get_user()
    except Exception as e:
        # use the exception message to get the account ID the function executes under
        account_ids.append(re.search(r'(arn:aws:sts::)([0-9]+)', str(e)).groups()[1])

    today_fmt = datetime.date.today().strftime('%Y-%m-%d')

    filters = [
        {'Name': 'tag:CreatedOn', 'Values': [today_fmt]},
        {'Name': 'tag:Type', 'Values': ['Automated']},
        {'Name': 'tag:BackupCrossRegion', 'Values': ['*']}
    ]
    snapshot_response = ec.describe_snapshots(OwnerIds=account_ids, Filters=filters)

    for snap in snapshot_response['Snapshots']:

        print("\tCopying %s created from %s of [%s]" % (snap['SnapshotId'], source_region, snap['Description']))

        target_regions = [
            t.get('Value') for t in snap['Tags']
            if t['Key'] == 'BackupCrossRegion'][0]

        for target in target_regions.split(','):
            print("\t\tto %s" % target)

            addl_ec = boto3.client('ec2', region_name=target)

            addl_snap = addl_ec.copy_snapshot(
                SourceRegion=source_region,
                SourceSnapshotId=snap['SnapshotId'],
                Description=snap['Description'],
                DestinationRegion=target
            )

            addl_ec.create_tags(
                Resources=[addl_snap['SnapshotId']],
                Tags=snap['Tags']
            )

            addl_ec.delete_tags(
                Resources=[addl_snap['SnapshotId']],
                Tags=[{"Key": "BackupCrossRegion"}]
            )

            addl_ec.create_tags(
                Resources=[addl_snap['SnapshotId']],
                Tags=[{'Key': 'BackupFromRegion', 'Value': source_region}]
            )