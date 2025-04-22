# S3 Ransomware Simulator

This project is divided in two parts: the actual S3 Ransomware Simulator, and a Cloud Detection and Response (CDR) suggested Infrastructure as Code for this type of attack.


## Simulator

This Python script simulates a ransomware attack on Amazon S3 buckets by encrypting all objects in a bucket using Server-Side Encryption with Customer-Provided Keys (SSE-C). It demonstrates how to programmatically encrypt objects, check permissions, and drop a ransom note.

### Features

- **Bucket Listing**: Lists all S3 buckets in the AWS account.
- **Permission Check**: Verifies if the bucket has `GetObject` and `PutObject` permissions.
- **Object Encryption**: Encrypts all objects in a bucket using SSE-C with a randomly generated AES-256 key.
- **Ransom Note**: Drops a ransom note in the bucket after encryption.
- **Key Management**: Saves the encryption key to a file for recovery purposes.

### Prerequisites

- **Python Version**: Python 3.x
- **AWS Credentials**: Ensure AWS credentials are configured in your environment (e.g., `~/.aws/credentials` or environment variables).
- **Dependencies**: Install the required Python libraries:

```bash
pip install boto3 botocore
```

### Usage
Run the script with the following options:

```bash
python3 attacker.py [OPTIONS]
```

Options
- `--bucket-name <bucket_name>`: Specify a single bucket to process.
- `--all-buckets`: Process all buckets in the AWS account.
- `--encrypt-objects`: Encrypt all objects in the specified bucket(s) using SSE-C.

### Examples

**Encrypt Objects in a Specific Bucket**

```bash
python3 attacker.py --bucket-name my-bucket --encrypt-objects
```

**Encrypt Objects in All Buckets**

```bash
python attacker.py --all-buckets --encrypt-objects
```

**Check a Bucket, but not encrypt the object**

```bash
python3 attacker.py --bucket-name my-bucket
```

### Output

The script provides detailed output during execution, including:

- Generated AES-256 encryption key and its MD5 hash.
- Permissions check results for each bucket.
- Number of files encrypted in each bucket.
- Confirmation of the ransom note being dropped.
- Location of the saved encryption key.

Example output:

```bash
S3 Bucket Encryption Tool with SSE-C

Processing specified bucket: my-bucket
Generated AES-256 encryption key for SSE-C: M+a4reQycj3pBBZyYs1KE9XpOcdyT7kGq1Mu+q5u+vM=
Key MD5: S2k8nSe8W9C7A2JO+Nr4mw==

Checking bucket: my-bucket
  GetObject permission: Yes
  PutObject permission: Yes

Processing bucket: my-bucket
  Encrypting: file1.txt
  Encrypting: file2.txt
  Encrypted 2 files in my-bucket using SSE-C
  Ransom note dropped in my-bucket.

Encryption key saved to [encryption_key.bin](http://_vscodecontentref_/3)
WARNING: This key is required to decrypt your files. Store it securely!

Encryption complete. Total files encrypted: 2
Warning: Without the encryption key, your files cannot be recovered!
```

### Key Management
The encryption key is saved to a file named encryption_key.bin in the current directory. This key is required to decrypt the files. Store it securely!

### Notes
The script is intended for educational purposes only. 
Ensure you have appropriate permissions to access and modify the S3 buckets you are working with.
The script skips objects that are already encrypted or are directories.


## Cloud Detection and Response (CDR) Infrastructure

This CloudFormation template (`cdr.yaml`) defines a Cloud Detection and Response (CDR) infrastructure to monitor and respond to suspicious S3 copy operations. It leverages AWS services such as CloudTrail, EventBridge, and Step Functions to detect and mitigate potential security threats.

### Features

- **CloudTrail Monitoring**: Tracks S3 copy operations (`CopyObject` and `CompleteMultipartUpload`) in a specified bucket.
- **EventBridge Rule**: Filters CloudTrail events for S3 copy operations and triggers a Step Function.
- **Step Function Workflow**: Handles detected events by:
  - Disabling IAM user access keys.
  - Quarantining IAM roles by attaching a restrictive policy.
  - Blocking `s3:PutObject` actions for compromised roles.
- **Secure Logging**: Stores CloudTrail logs in an encrypted S3 bucket with restricted public access.

### Parameters

- **`BucketName`**: The name of the S3 bucket to monitor for copy events. Defaults to `raphabot-no-ransomware`.

### Resources

#### IAM Roles

1. **EventBridgeStepFunctionRole**: Grants EventBridge permission to invoke the Step Function.
2. **StateMachineExecutionRole**: Grants the Step Function permission to manage IAM users and roles.

#### Step Function

- **`CopyObjectEventHandlerStateMachine`**: A state machine that:
  - Identifies the principal type (IAM user or assumed role).
  - Disables active access keys for IAM users.
  - Quarantines IAM roles by attaching a restrictive policy.
  - Blocks `s3:PutObject` actions for compromised roles.

#### CloudTrail

- **`S3CopyActivityTrail`**: Monitors S3 copy operations and logs them to an encrypted S3 bucket.

#### S3 Bucket

- **`CloudTrailBucket`**: Stores CloudTrail logs securely with encryption and public access restrictions.
- **`CloudTrailBucketPolicy`**: Grants CloudTrail permission to write logs to the bucket.

#### EventBridge Rule

- **`S3CopyEventRule`**: Filters S3 copy operations from CloudTrail and triggers the Step Function.

### Outputs

- **`StateMachineArn`**: ARN of the Step Function handling copy events.
- **`CloudTrailName`**: Name of the CloudTrail monitoring copy operations.
- **`EventRuleARN`**: ARN of the EventBridge rule.

### Deployment

1. Deploy the CloudFormation template using the AWS Management Console, AWS CLI, or SDKs.
2. Provide the `BucketName` parameter to specify the S3 bucket to monitor.

#### AWS CLI Example

```bash
aws cloudformation deploy \
  --template-file cdr.yaml \
  --stack-name CDR-Infrastructure \
  --parameter-overrides BucketName=my-s3-bucket
```

### How It Works

1. Event Detection: CloudTrail logs S3 copy operations in the specified bucket.
2. Event Filtering: EventBridge filters relevant events and triggers the Step Function.
3. Response: The Step Function disables IAM user keys or quarantines IAM roles involved in the operation.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
