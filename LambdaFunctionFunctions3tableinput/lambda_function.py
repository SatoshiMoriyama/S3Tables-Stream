import json
import boto3
import uuid
import os
from datetime import datetime
import logging

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境変数から設定を取得
FIREHOSE_DELIVERY_STREAM_NAME = os.environ.get('FIREHOSE_DELIVERY_STREAM_NAME', 'my-delivery-stream')

def lambda_handler(event, context):
    """
    Kinesis Firehoseにログデータを送信するLambda関数
    """
    
    try:
        # Firehoseクライアントを初期化
        firehose_client = boto3.client('firehose')
        
        # デバッグ: 受信したeventをログ出力
        logger.info(f"受信したevent: {json.dumps(event)}")
        
        # 送信するログデータを準備
        log_data = prepare_log_data(event)
        logger.info(f"送信データ準備完了 - ActivityId: {log_data.get('activity_id')}, UserId: {log_data.get('user_id')}")
        
        # Firehoseにデータを送信
        record_id = send_to_firehose(firehose_client, log_data)
        
        logger.info(f"データ送信完了 - Stream: {FIREHOSE_DELIVERY_STREAM_NAME}, RecordId: {record_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ログデータが正常にFirehoseに送信されました',
                'record_id': record_id
            })
        }
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def prepare_log_data(event):
    """
    イベントデータから操作ログデータを準備
    """
    # イベントから必要な情報を抽出
    current_time = datetime.utcnow()
    
    # API Gatewayからのリクエストの場合、bodyを解析
    if 'body' in event and event['body']:
        try:
            body_data = json.loads(event['body'])
            logger.info(f"API Gateway body parsed: {body_data}")
        except json.JSONDecodeError:
            logger.warning("Failed to parse request body as JSON")
            body_data = {}
    else:
        # 直接呼び出しの場合はeventをそのまま使用
        body_data = event
        logger.info(f"Direct invocation, using event as body_data")
    
    log_record = {
        'activity_id': body_data.get('activity_id', str(uuid.uuid4())),
        'created_at': current_time.isoformat(),
        'user_id': body_data.get('user_id', 'unknown'),
        'action_name': body_data.get('action_name', 'lambda_execution'),
        'entity_type': body_data.get('entity_type', 'system'),
        'entity_id': body_data.get('entity_id', 'lambda'),
        'success': body_data.get('success', True),
        'response_time_ms': body_data.get('response_time_ms', 0),
        'metadata': json.dumps(body_data.get('metadata', {}))
    }
    
    return log_record

def send_to_firehose(firehose_client, log_data):
    """
    Kinesis FirehoseにデータをPUT
    """
    if not log_data:
        raise ValueError("送信するデータがありません")
    
    # JSONデータを文字列に変換（Base64エンコードなし）
    json_data = json.dumps(log_data)
    
    # Firehoseにレコードを送信
    response = firehose_client.put_record(
        DeliveryStreamName=FIREHOSE_DELIVERY_STREAM_NAME,
        Record={
            'Data': json_data
        }
    )
    
    return response['RecordId']