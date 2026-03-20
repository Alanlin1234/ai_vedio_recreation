"""
测试图片生成API
"""
import requests

API_KEY = "sk-a7ce328257374b41afd201463d1413fa"

def test_text2image():
    """测试文生图"""
    print("=" * 50)
    print("测试 text2image API...")
    print("=" * 50)

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    data = {
        'model': 'wanx',
        'input': {
            'prompt': '一只可爱的小猫在草地上玩耍，阳光明媚，高清摄影风格'
        },
        'parameters': {
            'size': '1024*1024'
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n成功! 输出: {result}")

            # 下载图片
            if 'output' in result and 'image' in result['output']:
                img_url = result['output']['image']
                img_response = requests.get(img_url, timeout=30)
                if img_response.status_code == 200:
                    with open('test_output.png', 'wb') as f:
                        f.write(img_response.content)
                    print(f"图片已保存到 test_output.png")
            return True
        else:
            print(f"失败!")
            return False

    except Exception as e:
        print(f"异常: {e}")
        return False

def test_qwen_image_max():
    """测试 qwen-image-max"""
    print("\n" + "=" * 50)
    print("测试 qwen-image-max API...")
    print("=" * 50)

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    data = {
        'model': 'qwen-image-max',
        'input': {
            'prompt': '一只可爱的小猫在草地上玩耍，阳光明媚，高清摄影风格'
        },
        'parameters': {
            'size': '1024*1024'
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n成功! 输出: {result}")
            return True
        else:
            print(f"失败!")
            return False

    except Exception as e:
        print(f"异常: {e}")
        return False

if __name__ == "__main__":
    print("测试阿里云图片生成API")
    print(f"API Key: {API_KEY[:10]}...")

    # 测试 wanx
    success1 = test_text2image()

    # 测试 qwen-image-max
    success2 = test_qwen_image_max()

    print("\n" + "=" * 50)
    print("测试结果:")
    print(f"  wanx: {'成功' if success1 else '失败'}")
    print(f"  qwen-image-max: {'成功' if success2 else '失败'}")
