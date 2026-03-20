"""
测试 qwen-image-2.0
"""
import json
import os
from dashscope import MultiModalConversation
import dashscope

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
dashscope.api_key = "sk-a7ce328257374b41afd201463d1413fa"

print("=" * 50)
print("测试 qwen-image-2.0 文生图")
print("=" * 50)

messages = [
    {
        "role": "user",
        "content": [
            {"text": "一只可爱的小猫在草地上玩耍，阳光明媚，高清摄影风格"}
        ]
    }
]

response = MultiModalConversation.call(
    api_key=dashscope.api_key,
    model="qwen-image-2.0",
    messages=messages,
    result_format='message',
    stream=False,
    n=1,
    watermark=False
)

print(f"状态码: {response.status_code}")

if response.status_code == 200:
    content = response.output.choices[0].message.content
    print(f"Content: {content}")

    # 从 content[0].image 获取 URL
    if isinstance(content, list) and len(content) > 0:
        img_url = content[0].get('image') if isinstance(content[0], dict) else None
        if img_url:
            print(f"图片URL: {img_url}")

            # 下载图片
            import requests
            img_response = requests.get(img_url, timeout=30)
            if img_response.status_code == 200:
                with open('test_qwen_image2_output.png', 'wb') as f:
                    f.write(img_response.content)
                print(f"已保存到 test_qwen_image2_output.png")
            else:
                print(f"下载失败: {img_response.status_code}")
        else:
            print("未找到图片URL")
    else:
        print("content 格式异常")
else:
    print(f"失败: {response}")
