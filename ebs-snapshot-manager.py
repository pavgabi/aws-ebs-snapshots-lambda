import boto3
import re
import datetime
import time

ec = boto3.client('ec2')
iam = boto3.client('iam')

"""
This function looks at *all* snapshots that have the tags "Type:Automated" and
"DeleteOn" containing the current day formatted as YYYY-MM-DD. The function will
delete the if the todays date is > than the "DeleteOn".
"""


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

    today = datetime.datetime.now()

    print("\tDelete snapshots < %s " % today)

    filters = [
        {'Name': 'tag:Type', 'Values': ['Automated']},
    ]
    snapshot_response = ec.describe_snapshots(OwnerIds=account_ids, Filters=filters)

    for snap in snapshot_response['Snapshots']:
        skipping_this_one = False
        snapshot_delete_on = ""

        for tag in snap['Tags']:
            if tag['Key'] == 'KeepForever':
                skipping_this_one = True
            if tag['Key'] == 'DeleteOn':
                snapshot_delete_on = tag['Value']

        if skipping_this_one == True:
            print("\tSkipping snapshot %s marked KeepForever" % (snap['SnapshotId']))
            # do nothing else
        else:
            if snapshot_delete_on == "":
                print("\There is no DeleteOn Tag for this backup: %s" % (snap['SnapshotId']))
                continue

            snapshot_expires = datetime.datetime.strptime(snapshot_delete_on, "%Y-%m-%d")

            if snapshot_expires < today:
                print("\tDeleting %s with expiry date %s" % (snap['SnapshotId'], snapshot_delete_on))
                ec.delete_snapshot(SnapshotId=snap['SnapshotId'])
            else:
                print("\tKeeping %s until %s" % (snap['SnapshotId'], snapshot_delete_on))