"""
测试 qwen-image 系列模型
"""
import requests

API_KEY = "sk-a7ce328257374b41afd201463d1413fa"

def test_model(model_name, prompt="一只可爱的小猫在草地上玩耍，阳光明媚，高清摄影风格"):
    """测试指定模型"""
    print(f"\n测试 model={model_name}")

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    data = {
        'model': model_name,
        'input': {'prompt': prompt},
        'parameters': {'size': '1024*1024'}
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        print(f"  状态码: {response.status_code}")
        result = response.json()
        print(f"  响应: {result}")

        if response.status_code == 200 and 'output' in result and 'image' in result['output']:
            img_url = result['output']['image']
            img_response = requests.get(img_url, timeout=30)
            if img_response.status_code == 200:
                with open(f'test_{model_name}.png', 'wb') as f:
                    f.write(img_response.content)
                print(f"  ✅ 成功! 图片已保存到 test_{model_name}.png")
            return True
        elif 'code' in result:
            print(f"  ❌ 失败: {result.get('code')} - {result.get('message')}")
            return False
        else:
            print(f"  ❌ 未知响应格式")
            return False

    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return False

if __name__ == "__main__":
    print("测试 qwen-image 系列模型")
    print(f"API Key: {API_KEY[:10]}...")

    models = [
        "qwen-image",
        "qwen-image-v1",
        "qwen-image-v2",
        "qwen-vl",
        "qwen-vl-plus",
        "qwen-vl-max",
        "qwen-vl-flash",
    ]

    results = {}
    for model in models:
        results[model] = test_model(model)

    print("\n" + "=" * 50)
    print("测试结果汇总:")
    for model, success in results.items():
        print(f"  {model}: {'✅ 成功' if success else '❌ 失败'}")
