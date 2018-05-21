from __future__ import print_function
import boto3
import os
import sys
import uuid
from PIL import Image, ImageDraw, ImageFont
import PIL.Image
from datetime import datetime

s3_client = boto3.client('s3')
bucket_name = 'enphoto-dev'

def resize_image(image_path, resized_path):
    with Image.open(image_path) as image:
        # TODO: サムネイルサイズの計算処理を入れる
        # image.thumbnail(tuple(x / 2 for x in image.size))
        image.thumbnail((500, 500))
        image.save(resized_path)

def add_water_mark(image_path):
    # s3からウォーターマークを取ってくる
    watermark_path = 'watermark.png'
    watermark_tmp_path = '/tmp/watermark.png'
    s3_client.download_file(bucket_name, watermark_path, watermark_tmp_path)

    # サムネイルにくっつける
    thumbnail = Image.open(image_path)
    watermark = Image.open(watermark_tmp_path)
    mask = watermark.split()[3] # pngを透過させるためにマスクを指定する

    thumbnail.paste(watermark, (thumbnail.width - 200, thumbnail.height - 50), mask)
    upload_path = '/tmp/watered_{}.jpg'.format(uuid.uuid4())
    thumbnail.save(upload_path, quality=95)
    s3_client.upload_file(upload_path, '{}'.format(bucket_name), 'lambda_thumbnail/water_{}.jpg'.format(datetime.now().strftime("%Y%m%d%H%M%S")))
    return upload_path

def pad_white(image_path):
    thumbnail = Image.open(image_path)

    # 500*500の白い背景を作る
    pad = Image.new('RGBA', (500, 500), (255, 255, 255, 0))
    # ウォーターマークをつけたサムネイルを、白背景にpasteする
    pad.paste(thumbnail, (0, int((500-thumbnail.height)/2)))
    upload_path = '/tmp/pad_{}.jpg'.format(uuid.uuid4())
    pad = pad.convert('RGB')
    pad.save(upload_path, quality=95)
    s3_client.upload_file(upload_path, '{}'.format(bucket_name), 'lambda_thumbnail/pad_{}.jpg'.format(datetime.now().strftime("%Y%m%d%H%M%S")))

def lambda_handler(event, context):
    for record in event['Records']:
        object_key = record['s3']['object']['key']

        download_path = '/tmp/{}.jpg'.format(uuid.uuid4()) #ダウンロードしたファイルをおくパス(lambda側のパス) ファイル名をuuidにする
        upload_path = '/tmp/resized-{}.jpg'.format(uuid.uuid4()) #アップロードするファイルのパス(lambdaのパス) ファイル名をresized-<uuid>

        #s3_client.download_file('enphoto-dev', 'original/1/1/00298f38-3ea1-4e49-bd2e-3ab8e733c28b.jpg', '/tmp/test.jpg')
        s3_client.download_file(bucket_name, object_key, download_path)
        # リサイズする
        resize_image(download_path, upload_path)
        # ウォーターマークをくっつける(s3においておく)
        water_upload_path = add_water_mark(upload_path)
        # サムネイルサイズに達していない場合、周りを白背景にする
        pad_white(water_upload_path)

        s3_client.upload_file(upload_path, '{}'.format(bucket_name), 'lambda_thumbnail/{}.jpg'.format(datetime.now().strftime("%Y%m%d%H%M%S")))
